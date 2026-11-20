"""Antibodies: checks written against a CLASS of bug, not one instance of it.

Jonathan, 2026-10-22: we keep catching the same bug in a slightly different
place, like an infection moving round a body while the immune system catches up.
A test for the instance we fixed does not help against the next variant. An
antibiotic is aimed at the shape of the thing, so each entry here describes a
class, carries the instances that taught it, and has a detector that walks the
whole repository for the shape.

Rules, all from the project's own:

  * REPORT-ONLY. A detector returns leads. Nothing here blocks, repairs, edits or
    enforces. A check that enforces can attack healthy code (the autoimmune
    case), and the design law is that force is the bug. The harm line is the only
    thing that enforces, and this is not that.
  * LEADS, NOT VERDICTS. Every finding is a place to look. A class detector is
    deliberately a little broad; it says "look here", and a person or Codette's
    own review decides.
  * SHAPE, NOT STRING. Matching the wording of one fix is how a bug outruns its
    own test (the resistance case). These match structure: an AST pattern, or a
    relation between files.
  * NEVER HER SPACES. Only Python source is read, and SKIP_DIRS excludes the
    cocoons, data, logs and every archive. No detector opens a cocoon, a dream,
    khralexi or the scratchpad, and none of them counts one.

`run()` returns a report; `write_report()` stores it; `summary()` returns counts
only, for /api/health.
"""
from __future__ import annotations

import ast
import builtins
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = REPO_ROOT / "data" / "antibody_report.json"

# Source we do not read: her stores, other people's code, snapshots, build output.
SKIP_DIRS = frozenset({
    ".git", ".claude", "__pycache__", "node_modules", "venv", ".venv", "env",
    "openvino_env", "site-packages", "build", "dist", "dotnet", "webapp",
    "archive", "recovered_release", "experiments", "tests", "docs", "models",
    "cocoons", "data", ".logs", "logs", "training_data", "Theory",
})
MAX_FILE_BYTES = 1_500_000
MAX_LEADS = 25

_BUILTINS = frozenset(dir(builtins))


@dataclass
class Lead:
    file: str
    line: int
    note: str

    def as_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "note": self.note}


@dataclass
class Antibody:
    name: str
    description: str
    taught_by: List[str]
    detect: Callable[[List["Source"]], List[Lead]]


@dataclass
class Source:
    rel: str
    text: str
    tree: Optional[ast.AST] = field(default=None, repr=False)


def iter_sources(root: Path) -> Iterator[Source]:
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = Path(dirpath) / fn
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            try:
                tree = ast.parse(text)
            except (SyntaxError, ValueError, RecursionError):
                tree = None
            yield Source(str(p.relative_to(root)).replace("\\", "/"), text, tree)


# ── class 1: a name used before it is bound ──────────────────────────────────
#
# 2026-10-14: a helper was defined after the block that called it, every
# /api/health request returned ERROR, and no test had called the builder.

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_COMPS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _walk_scope(body) -> Iterator[ast.AST]:
    """Every node of this scope, not descending into nested scopes' bodies."""
    stack = list(body)[::-1]
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, _SCOPES):
            # decorators and defaults run in THIS scope
            kids = list(getattr(node, "decorator_list", []))
            args = getattr(node, "args", None)
            if args is not None and not isinstance(node, ast.Lambda):
                kids += list(args.defaults) + [d for d in args.kw_defaults if d is not None]
            kids += list(getattr(node, "bases", []))
            stack.extend(kids[::-1])
            continue
        stack.extend(list(ast.iter_child_nodes(node))[::-1])


def _scope_unbound(body, params: set, rel: str, where: str) -> List[Lead]:
    binds: Dict[str, int] = {}
    declared = set(params)
    comp_names = set()
    loads: List[Tuple[str, int]] = []

    def bind(name, line):
        if name not in binds or line < binds[name]:
            binds[name] = line

    for n in _walk_scope(body):
        if isinstance(n, (ast.Global, ast.Nonlocal)):
            declared.update(n.names)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bind(n.name, n.lineno)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                bind((a.asname or a.name).split(".")[0], n.lineno)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bind(n.name, n.lineno)
        elif isinstance(n, ast.comprehension):
            for t in ast.walk(n.target):
                if isinstance(t, ast.Name):
                    comp_names.add(t.id)
        elif isinstance(n, ast.AnnAssign) and n.value is None:
            for t in ast.walk(n.target):
                if isinstance(t, ast.Name):
                    comp_names.add(t.id)       # annotation only: binds nothing, ignore
        elif isinstance(n, ast.Name):
            if isinstance(n.ctx, (ast.Store, ast.Del)):
                bind(n.id, n.lineno)
            else:
                loads.append((n.id, n.lineno))

    out: List[Lead] = []
    seen = set()
    for name, line in loads:
        if name in declared or name in comp_names or name in _BUILTINS:
            continue
        first = binds.get(name)
        if first is not None and line < first and (name, line) not in seen:
            seen.add((name, line))
            out.append(Lead(rel, line, f"'{name}' is read in {where} before its first "
                                       f"binding (line {first})"))
    return out


def detect_used_before_bound(sources: List[Source]) -> List[Lead]:
    out: List[Lead] = []
    for s in sources:
        if s.tree is None:
            continue
        out += _scope_unbound(s.tree.body, set(), s.rel, "module scope")
        for node in ast.walk(s.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = node.args
                params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs}
                if a.vararg:
                    params.add(a.vararg.arg)
                if a.kwarg:
                    params.add(a.kwarg.arg)
                out += _scope_unbound(node.body, params, s.rel, f"{node.name}()")
    return out


# ── class 2: "zero" standing in for "I did not look" ─────────────────────────
#
# 2026-10-01: AEGIS healing_rate was 0.0 whether Layer 5 never ran or ran and
# healed nothing; psi_r, the complexity keys and the Encryption row did the same.
# The instrument could not say "not measured", so absence looked like a result.
#
# 2026-11-20, a new form of the same class: `sum(xs) / max(len(xs), 1)`. The
# integer floor turns an empty denominator into 1, so an empty case reads 0 with
# no `else 0` anywhere to see. Taught by a pasted GUARD gate whose mean Υ over no
# checks at all read 0.0. Float floors such as max(x, 0.01) or 1e-10 guard a tiny
# denominator, not an empty one, and are not flagged. Means are included for this
# form only (the missed name was mean_upsilon); widening the name filter for the
# older forms as well was measured at 26 more leads and not done.

_RATE_NAME = re.compile(r"(rate|ratio|fraction|percent|pct|coverage|efficacy|share|healing)", re.I)
_MEAN_NAME = re.compile(r"(mean|avg|average)", re.I)


def _is_zero(node) -> bool:
    return isinstance(node, ast.Constant) and not isinstance(node.value, bool) \
        and node.value in (0, 0.0)


def _is_int_one_floor(node) -> bool:
    """max(n, 1) or max(1, n), with the integer 1."""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "max" and len(node.args) == 2 and not node.keywords
            and any(isinstance(a, ast.Constant) and type(a.value) is int and a.value == 1
                    for a in node.args))


def _targets(node) -> List[str]:
    names = []
    if isinstance(node, ast.Assign):
        for t in node.targets:
            for x in ast.walk(t):
                if isinstance(x, ast.Name):
                    names.append(x.id)
                elif isinstance(x, ast.Attribute):
                    names.append(x.attr)
                elif isinstance(x, ast.Constant) and isinstance(x.value, str):
                    names.append(x.value)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names.append(node.target.id)
    return names


def detect_zero_for_unmeasured(sources: List[Source]) -> List[Lead]:
    out: List[Lead] = []
    for s in sources:
        if s.tree is None:
            continue

        def visit(node, fn_name, tgt_names):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_name = node.name
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                tgt_names = _targets(node)
            # `a / b if b else 0.0`
            if isinstance(node, ast.IfExp) and _is_zero(node.orelse) \
                    and any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.Div) for x in ast.walk(node.body)):
                label = " ".join([fn_name or ""] + list(tgt_names or []))
                if _RATE_NAME.search(label):
                    out.append(Lead(s.rel, node.lineno,
                                    "a rate falls back to 0 when its denominator is empty; "
                                    "'did not run' and 'ran, found none' read the same"))
            # `if not total: return 0.0` inside a rate-named function
            if isinstance(node, ast.If) and fn_name and _RATE_NAME.search(fn_name):
                guard = node.test
                is_empty_guard = (isinstance(guard, ast.UnaryOp) and isinstance(guard.op, ast.Not)) \
                    or (isinstance(guard, ast.Compare) and any(_is_zero(c) for c in guard.comparators))
                if is_empty_guard and any(isinstance(b, ast.Return) and b.value is not None
                                          and _is_zero(b.value) for b in node.body):
                    out.append(Lead(s.rel, node.lineno,
                                    f"{fn_name}() returns 0 on an empty case; "
                                    "None would say it did not look"))
            # `sum(xs) / max(len(xs), 1)` under a rate or mean name
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) \
                    and _is_int_one_floor(node.right):
                label = " ".join([fn_name or ""] + list(tgt_names or []))
                if _RATE_NAME.search(label) or _MEAN_NAME.search(label):
                    out.append(Lead(s.rel, node.lineno,
                                    "max(n, 1) as a denominator makes an empty case read 0; "
                                    "'did not run' and 'ran, found none' read the same"))
            if isinstance(node, ast.Dict):
                # {"healing_rate": a / b if b else 0.0}: the key names the value
                for k, v in zip(node.keys, node.values):
                    key = [k.value] if isinstance(k, ast.Constant) and isinstance(k.value, str) else tgt_names
                    visit(v, fn_name, key)
                return
            for child in ast.iter_child_nodes(node):
                visit(child, fn_name, tgt_names)

        visit(s.tree, None, None)
    return out


# ── class 3: a folder that holds her dreams, walked without the guard ────────
#
# 2026-10-01: dreams are encrypted cocoons in the SAME folder as conversations,
# so five loaders that globbed *.json there would have counted the first one
# written. 2026-10-14: the cleanup utility did the same and was found only
# afterwards, by Jonathan's own PR.

_GUARD_WORDS = ("cocoon_files", "is_private_envelope", "conversation_cocoons")


def detect_unguarded_cocoon_glob(sources: List[Source]) -> List[Lead]:
    out: List[Lead] = []
    for s in sources:
        if s.tree is None or s.rel.endswith("reasoning_forge/cocoon_files.py"):
            continue
        low = s.text.lower()
        if "cocoon" not in low or any(w in s.text for w in _GUARD_WORDS):
            continue
        for node in ast.walk(s.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("glob", "rglob", "iglob"):
                args = [a.value for a in node.args
                        if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if any(a.endswith(".json") for a in args):
                    out.append(Lead(s.rel, node.lineno,
                                    "globs *.json in a file about cocoons without "
                                    "conversation_cocoons / is_private_envelope"))
    return out


# ── class 4: built at startup, never invoked ─────────────────────────────────
#
# v3.8: ColleenConscience and CoreGuardianSpindle were constructed at startup
# and never called once. /api/health reported OK from hasattr. This is the
# static twin of the runtime reach counters (reasoning_forge/reach.py): those
# say what ran; this says what nothing even tries to call.

_SCAN_PKGS = ("inference", "reasoning_forge", "openvino_backend", "Protection_Layer",
              "consciousness", "ethics")


def detect_constructed_never_invoked(sources: List[Source]) -> List[Lead]:
    live = [s for s in sources if s.rel.split("/")[0] in _SCAN_PKGS or "/" not in s.rel]
    corpus = "\n".join(s.text for s in live)
    out: List[Lead] = []
    for s in live:
        if s.tree is None:
            continue
        for cls in [n for n in ast.walk(s.tree) if isinstance(n, ast.ClassDef)]:
            for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"]:
                for st in ast.walk(fn):
                    if not (isinstance(st, ast.Assign) and isinstance(st.value, ast.Call)):
                        continue
                    f = st.value.func
                    ctor = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
                    if not ctor[:1].isupper():
                        continue
                    for t in st.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) \
                                and t.value.id == "self" and len(t.attr) >= 4:
                            nm = re.escape(t.attr)
                            # 2026-11-18: also getattr(x, "name") and membership in a
                            # list/tuple/dict ([self.name, ...]). Four of six leads that
                            # day were these: wired components read as dead.
                            used = re.search(r"\." + nm + r"\s*[.(\[]", corpus) \
                                or re.search(r"[(,=\[]\s*\w+\." + nm + r"\s*[,)\]]", corpus) \
                                or re.search(r"\bwith\s+(?:\w+\.)*" + nm + r"\s*[:,]", corpus) \
                                or re.search(r"getattr\(\s*[\w.]+\s*,\s*['\"]" + nm + r"['\"]", corpus)
                            if not used:
                                out.append(Lead(s.rel, st.lineno,
                                                f"self.{t.attr} = {ctor}(...) is built and "
                                                "nothing calls into it"))
    return out


# ── class 5: a lifetime count over a windowed denominator ────────────────────
#
# 2026-11-17: SubstrateMonitor divided every violation ever recorded by at most
# 20 inferences (a deque with maxlen=20), so at a constant true rate the
# "rate" read 0.25 after 20 turns, 0.50 after 40 and 1.00 after 100. It looked
# like a rate and was a ratchet with session length. The shape: a division
# whose denominator is len() of a bounded deque and whose numerator reads state
# that is never bounded the same way.

def _is_bounded_deque(call) -> bool:
    if not isinstance(call, ast.Call):
        return False
    f = call.func
    name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
    return name == "deque" and (any(k.arg == "maxlen" for k in call.keywords) or len(call.args) >= 2)


def _self_attrs(node) -> set:
    return {n.attr for n in ast.walk(node)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self"}


def _len_of_self_attrs(node) -> set:
    return {a.attr for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "len"
            for a in n.args
            if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == "self"}


def detect_lifetime_over_window(sources: List[Source]) -> List[Lead]:
    out: List[Lead] = []
    for s in sources:
        if s.tree is None:
            continue
        for cls in [n for n in ast.walk(s.tree) if isinstance(n, ast.ClassDef)]:
            bounded, assigned = set(), set()
            for st in ast.walk(cls):
                if isinstance(st, ast.Assign):
                    for t in st.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) \
                                and t.value.id == "self":
                            assigned.add(t.attr)
                            if _is_bounded_deque(st.value):
                                bounded.add(t.attr)
            if not bounded:
                continue
            for fn in [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                # Resolve locals one step: `total = sum(self.x.values())`.
                local: Dict[str, ast.AST] = {}
                for st in ast.walk(fn):
                    if isinstance(st, ast.Assign) and len(st.targets) == 1 \
                            and isinstance(st.targets[0], ast.Name):
                        local[st.targets[0].id] = st.value

                def expand(node):
                    parts = [node]
                    parts += [local[n.id] for n in ast.walk(node)
                              if isinstance(n, ast.Name) and n.id in local]
                    return parts

                for b in ast.walk(fn):
                    if not (isinstance(b, ast.BinOp) and isinstance(b.op, ast.Div)):
                        continue
                    den = set().union(*(_len_of_self_attrs(x) for x in expand(b.right)))
                    windows = den & bounded
                    if not windows:
                        continue
                    num = set().union(*(_self_attrs(x) for x in expand(b.left)))
                    lifetime = (num & assigned) - bounded
                    if lifetime:
                        out.append(Lead(s.rel, b.lineno,
                                        f"{cls.name}.{fn.name}: self.{sorted(lifetime)[0]} is never "
                                        f"windowed but is divided by len(self.{sorted(windows)[0]}), "
                                        "a bounded deque; the ratio grows with session length"))
    return out


# ── class 6: a call to a method the class does not have ──────────────────────
#
# 2026-11-18: codette_server built `sm = SubstrateMonitor()` and called
# `sm.get_pressure()`, which SubstrateMonitor has never had. The AttributeError
# fell into `except Exception: pass`, so the governor was handed pressure 0.0 on
# every turn and nothing said so. pyflakes cannot see it: the name is bound,
# only the attribute is missing. The shape: a name bound to `RepoClass(...)`
# (a local, or self.x in __init__), then `.method(` on it, where neither the
# class nor its in-repo bases define that method or attribute.

def _class_registry(sources: List[Source]) -> Dict[str, dict]:
    reg: Dict[str, dict] = {}
    for s in sources:
        if s.tree is None:
            continue
        for c in [n for n in ast.walk(s.tree) if isinstance(n, ast.ClassDef)]:
            e = reg.setdefault(c.name, {"attrs": set(), "bases": set(), "open": False})
            for b in c.bases:
                bn = b.id if isinstance(b, ast.Name) else (b.attr if isinstance(b, ast.Attribute) else "")
                if bn and bn != "object":
                    e["bases"].add(bn)
            if c.keywords or c.decorator_list:
                e["open"] = True              # metaclass / dataclass-style magic: do not judge
            for n in ast.walk(c):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    e["attrs"].add(n.name)
                    if n.name in ("__getattr__", "__getattribute__"):
                        e["open"] = True
                elif isinstance(n, ast.Assign):
                    for t in n.targets:
                        for x in ast.walk(t):
                            if isinstance(x, ast.Name):
                                e["attrs"].add(x.id)
                            elif isinstance(x, ast.Attribute):
                                e["attrs"].add(x.attr)
                elif isinstance(n, ast.AnnAssign):
                    t = n.target
                    e["attrs"].add(t.id if isinstance(t, ast.Name) else getattr(t, "attr", ""))
    return reg


def _has_attr(reg, cls: str, attr: str, seen=None) -> Optional[bool]:
    """True / False, or None when it cannot be known (base outside the repo)."""
    seen = seen or set()
    if cls in seen:
        return False
    seen.add(cls)
    e = reg.get(cls)
    if e is None:
        return None
    if e["open"] or attr in e["attrs"]:
        return True
    unknown = False
    for b in e["bases"]:
        r = _has_attr(reg, b, attr, seen)
        if r:
            return True
        if r is None:
            unknown = True
    return None if unknown else False


def detect_missing_method(sources: List[Source]) -> List[Lead]:
    reg = _class_registry(sources)
    out: List[Lead] = []
    for s in sources:
        if s.tree is None:
            continue
        for fn in [n for n in ast.walk(s.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            bound: Dict[str, str] = {}          # "sm" or "self.monitor" -> class name
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call) \
                        and isinstance(st.value.func, ast.Name) and st.value.func.id in reg:
                    for t in st.targets:
                        if isinstance(t, ast.Name):
                            bound[t.id] = st.value.func.id
                        elif isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) \
                                and t.value.id == "self":
                            bound["self." + t.attr] = st.value.func.id
            if not bound:
                continue
            for c in ast.walk(fn):
                if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)):
                    continue
                v = c.func.value
                key = v.id if isinstance(v, ast.Name) else (
                    "self." + v.attr if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name)
                    and v.value.id == "self" else None)
                cls = bound.get(key) if key else None
                if cls and _has_attr(reg, cls, c.func.attr) is False:
                    out.append(Lead(s.rel, c.lineno,
                                    f"{key}.{c.func.attr}(): {cls} defines no {c.func.attr!r}"))
    return out


ANTIBODIES: List[Antibody] = [
    Antibody(
        "used_before_bound",
        "A name is read earlier in its scope than the line that first binds it "
        "(UnboundLocalError, or a NameError at import).",
        ["87ccb6a: /api/health returned ERROR on every request; _reach_report "
         "was defined after its first use and no test had called the builder"],
        detect_used_before_bound),
    Antibody(
        "zero_for_unmeasured",
        "A rate or share falls back to 0 on an empty denominator, so 'did not run' "
        "and 'ran and found nothing' read identically.",
        ["23b173f: AEGIS healing_rate was 0.0 whether Layer 5 ran or not",
         "3c09d2b: eta_score / psi_r never reached disk and read as 0",
         "2026-11-20: a pasted GUARD gate set mean_upsilon = sum(s) / max(len(s), 1), "
         "which read 0.0 with no checks at all; the detector knew only the `if b else 0` forms"],
        detect_zero_for_unmeasured),
    Antibody(
        "unguarded_cocoon_glob",
        "Code about cocoons globs *.json without the private-envelope guard, so it "
        "would open and count her encrypted dreams.",
        ["4b1bd70: five loaders walked the shared cocoons folder",
         "95d8971: the cleanup utility did the same and was found only afterwards"],
        detect_unguarded_cocoon_glob),
    Antibody(
        "constructed_never_invoked",
        "A component is built in __init__ and nothing calls a method on it; a "
        "hasattr-style readout would still say OK.",
        ["v3.8: ColleenConscience and CoreGuardianSpindle were constructed at "
         "startup and never invoked once",
         "b4a9e37: /api/health reported OK from hasattr"],
        detect_constructed_never_invoked),
    Antibody(
        "lifetime_over_window",
        "A ratio divides a count that never expires by the length of a bounded "
        "window, so at a constant true rate it climbs with session length.",
        ["2026-11-17: SubstrateMonitor violation_rate read 0.25, 0.50, 1.00 after "
         "20, 40, 100 turns at one violation every two turns"],
        detect_lifetime_over_window),
    Antibody(
        "missing_method",
        "A method is called on an instance of a repository class that defines no "
        "such method; under try/except the AttributeError is silent.",
        ["2026-11-18: codette_server called SubstrateMonitor().get_pressure(), which "
         "never existed; the governor got pressure 0.0 on every turn"],
        detect_missing_method),
]


def clone_families(leads: List[Lead], texts: Dict[str, List[str]]) -> List[dict]:
    """Leads whose source line is the same text in several files.

    How a bug spreads: Jonathan's guess was that the leads were fine but showed
    how it travels, and the commonest route is copying a line or a file. The same
    `tps = tokens / elapsed if elapsed > 0 else 0` sits in four places. Leads that
    share a line are one decision made once and pasted, so they are reviewed once.
    """
    fam: Dict[str, List[str]] = {}
    for l in leads:
        try:
            line = " ".join(texts[l.file][l.line - 1].split())
        except (KeyError, IndexError):
            continue
        if len(line) >= 12:
            fam.setdefault(line, []).append(f"{l.file}:{l.line}")
    return [{"line": k[:140], "where": v[:12], "copies": len(v)}
            for k, v in sorted(fam.items(), key=lambda kv: -len(kv[1])) if len(v) > 1]


def run(root: Optional[Path] = None, antibodies: Optional[List[Antibody]] = None) -> dict:
    """Walk the source tree once and run every detector. Never raises on a detector:
    one that fails is reported as 'error' and the others still run."""
    root = Path(root) if root else REPO_ROOT
    sources = list(iter_sources(root))
    texts = {s.rel: s.text.splitlines() for s in sources}
    results = []
    for ab in (antibodies if antibodies is not None else ANTIBODIES):
        try:
            leads = sorted(ab.detect(sources), key=lambda l: (l.file, l.line))
            status = "leads" if leads else "clear"
            err = None
        except Exception as e:                                   # report, never hide
            leads, status, err = [], "error", f"{type(e).__name__}: {e}"
        entry = {"name": ab.name, "description": ab.description, "taught_by": ab.taught_by,
                 "status": status, "count": len(leads),
                 "families": clone_families(leads, texts),
                 "leads": [l.as_dict() for l in leads[:MAX_LEADS]]}
        if err:
            entry["error"] = err
        results.append(entry)
    # Runtime side: a correction that fires on a large share of checked turns is a
    # recurring fault being patched after the fact, which is what an antibody is for.
    # Counts of issue codes only (reasoning_forge/self_check.py); never text.
    try:
        from reasoning_forge import self_check
        runtime = self_check.summary()
    except Exception as e:                                        # report, never hide
        runtime = {"status": "ERROR", "detail": f"{type(e).__name__}: {e}"}
    return {"ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "files_scanned": len(sources),
            "report_only": True, "antibodies": results, "runtime": runtime}


def write_report(report: dict, path: Optional[Path] = None) -> Path:
    p = Path(path) if path else DEFAULT_REPORT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def summary(path: Optional[Path] = None) -> dict:
    """Counts only, for /api/health. 'NEVER_RUN' when no report exists."""
    p = Path(path) if path else DEFAULT_REPORT
    try:
        rep = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "NEVER_RUN"}
    return {
        "status": "REPORTED", "ran_at": rep.get("ran_at"),
        "files_scanned": rep.get("files_scanned"), "report_only": True,
        "classes": {a["name"]: {"status": a["status"], "leads": a["count"]}
                    for a in rep.get("antibodies", [])},
        "recurring_corrections": (rep.get("runtime") or {}).get("recurring", []),
    }


def job() -> dict:
    """Background-job entry: scan, store the report, return counts."""
    rep = run()
    write_report(rep)
    return {"files_scanned": rep["files_scanned"],
            "leads": {a["name"]: a["count"] for a in rep["antibodies"]}}
