#!/usr/bin/env python3
"""Grounding — the verifying half of the mind.

Codette already CREATES thoughts (cocoon_synthesizer forges cross-domain
patterns; perspective_web spawns new nodes). This module VERIFIES them: it takes
a claim and returns a verdict grounded in a real solver, not the LLM's own
assertion. Intuition proposes; rigor disposes.

Design invariants (these are the point, not decoration):
  1. NEVER asserts truth it did not check. A claim it cannot formalize returns
     UNVERIFIABLE — never VERIFIED-by-default. Same omit-never-fabricate rule as
     LiveCognitionState.
  2. Pure and side-effect-free. verify() computes; it does not log, mutate, or
     gate anything. Shadow logging is a separate opt-in wrapper (log_shadow()).
  3. Degrades honestly. With sympy absent, every arithmetic claim is UNVERIFIABLE
     (not silently VERIFIED). A missing solver removes capability, never honesty.

Phase A1 backs arithmetic and algebraic (in)equalities with sympy. Logical
claims (z3) are Phase C3. See docs/NEUROSYMBOLIC_GROUNDING.md.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional

try:
    import sympy
    from sympy import Eq, simplify, sympify
    from sympy.core.sympify import SympifyError
    _HAS_SYMPY = True
except Exception:  # pragma: no cover - environment without sympy
    _HAS_SYMPY = False

try:
    import z3
    _HAS_Z3 = True
except Exception:  # pragma: no cover - environment without z3
    _HAS_Z3 = False


class Verdict(str, Enum):
    VERIFIED = "verified"        # formalized and confirmed true
    REFUTED = "refuted"          # formalized and confirmed false
    UNVERIFIABLE = "unverifiable"  # could not be formalized — NOT a truth claim


# Comparators we can formalize, longest-token-first so ">=" wins over ">".
_COMPARATORS = [
    ("==", "eq"), ("!=", "ne"),
    (">=", "ge"), ("<=", "le"),
    ("=", "eq"), (">", "gt"), ("<", "lt"),
]


@dataclass
class GroundingResult:
    """The outcome of grounding one claim. Carries WHY, always."""
    claim: str
    verdict: Verdict
    detail: str                       # human-readable reason
    method: str = "none"              # which backend produced the verdict
    normalized: Optional[str] = None  # the formalized form, when we got one
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d


def _split_comparison(claim: str) -> Optional[tuple]:
    """Split a claim into (lhs, op, rhs) on the first top-level comparator.

    Returns None if no comparator is present. Skips '==' inside '===' etc. by
    working on the normalized single form.
    """
    text = claim.strip()
    # Normalize a lone '=' that is not part of ==, >=, <=, != by handling via the
    # ordered comparator scan below (== is matched before =).
    for token, name in _COMPARATORS:
        idx = text.find(token)
        # require the comparator to have content on both sides
        if idx > 0 and idx + len(token) < len(text):
            lhs = text[:idx].strip()
            rhs = text[idx + len(token):].strip()
            # guard against matching the '=' inside '>=', '<=', '!=', '=='
            if token == "=" and (text[idx - 1] in "<>=!" or text[idx + 1:idx + 2] == "="):
                continue
            if lhs and rhs:
                return lhs, name, rhs
    return None


def verify(claim: str) -> GroundingResult:
    """Verify a single claim. Pure: no logging, no side effects.

    Only arithmetic/algebraic (in)equalities are formalizable in Phase A1.
    Anything else returns UNVERIFIABLE with a reason — never a default VERIFIED.
    """
    claim = (claim or "").strip()
    if not claim:
        return GroundingResult(claim, Verdict.UNVERIFIABLE, "empty claim")

    parsed = _split_comparison(claim)
    if parsed is None:
        return GroundingResult(
            claim, Verdict.UNVERIFIABLE,
            "no comparator found — not an (in)equality this backend can check",
        )

    if not _HAS_SYMPY:
        return GroundingResult(
            claim, Verdict.UNVERIFIABLE,
            "sympy not available — arithmetic grounding disabled (honest UNVERIFIABLE, not assumed true)",
        )

    lhs_s, op, rhs_s = parsed
    try:
        lhs = sympify(lhs_s)
        rhs = sympify(rhs_s)
    except (SympifyError, SyntaxError, TypeError, ValueError) as e:
        return GroundingResult(
            claim, Verdict.UNVERIFIABLE,
            f"could not parse into symbolic form: {e}",
        )

    normalized = f"{lhs} {op} {rhs}"
    try:
        if op == "eq":
            truth = simplify(lhs - rhs) == 0
        elif op == "ne":
            truth = simplify(lhs - rhs) != 0
        else:
            diff = simplify(lhs - rhs)
            # Concrete number: decide directly. Non-constant: hand to z3, which can
            # decide UNIVERSAL validity ("x**2 >= 0" is always true) — something the
            # sympy path cannot. If z3 is absent or the claim is merely contingent
            # ("x > 0"), we return UNVERIFIABLE, never a guess.
            if not diff.is_number:
                z3_verdict = _z3_ordering(lhs, rhs, op)
                if z3_verdict is not None:
                    return GroundingResult(
                        claim, z3_verdict,
                        f"z3 decided '{normalized}' over the reals: {z3_verdict.value}",
                        method="z3", normalized=normalized,
                    )
                return GroundingResult(
                    claim, Verdict.UNVERIFIABLE,
                    f"ordering of '{diff}' is contingent (depends on variable values) "
                    f"or not decidable by the available backend",
                    method="sympy", normalized=normalized,
                )
            val = float(diff)
            truth = {
                "gt": val > 0, "lt": val < 0,
                "ge": val >= 0, "le": val <= 0,
            }[op]
    except (TypeError, ValueError) as e:
        return GroundingResult(
            claim, Verdict.UNVERIFIABLE,
            f"symbolic evaluation could not decide: {e}",
            method="sympy", normalized=normalized,
        )

    verdict = Verdict.VERIFIED if truth else Verdict.REFUTED
    return GroundingResult(
        claim, verdict,
        f"sympy evaluated '{normalized}' as {truth}",
        method="sympy", normalized=normalized,
    )


# ── z3 layer: universal validity + cross-claim contradiction detection ──────

def _sympy_to_z3(expr, smap):
    """Translate a sympy arithmetic expression into a z3 real expression.

    Handles the subset our claims produce (numbers, symbols, +, *, integer
    powers, division). Raises ValueError on anything outside it — the caller
    treats that as 'cannot formalize' (honest UNVERIFIABLE), never as a guess.
    """
    if expr.is_number:
        return z3.RealVal(str(sympy.nsimplify(expr))) if expr.is_rational else z3.RealVal(float(expr))
    if expr.is_Symbol:
        name = str(expr)
        if name not in smap:
            smap[name] = z3.Real(name)
        return smap[name]
    if expr.is_Add:
        terms = [_sympy_to_z3(a, smap) for a in expr.args]
        out = terms[0]
        for t in terms[1:]:
            out = out + t
        return out
    if expr.is_Mul:
        out = None
        for a in expr.args:
            t = _sympy_to_z3(a, smap)
            out = t if out is None else out * t
        return out
    if expr.is_Pow:
        base, exp = expr.args
        if exp.is_Integer:
            e = int(exp)
            b = _sympy_to_z3(base, smap)
            if e == 0:
                return z3.RealVal(1)
            if e > 0:
                out = b
                for _ in range(e - 1):
                    out = out * b
                return out
            out = b
            for _ in range(-e - 1):
                out = out * b
            return z3.RealVal(1) / out
        raise ValueError(f"non-integer power {exp}")
    raise ValueError(f"untranslatable expression {expr}")


def _z3_rel(lhs_sym, rhs_sym, op, smap):
    """Build a z3 relational constraint from sympy lhs/rhs and an op name."""
    L = _sympy_to_z3(lhs_sym, smap)
    R = _sympy_to_z3(rhs_sym, smap)
    return {
        "eq": L == R, "ne": L != R,
        "gt": L > R, "lt": L < R, "ge": L >= R, "le": L <= R,
    }[op]


def _z3_ordering(lhs_sym, rhs_sym, op):
    """Decide a single relational claim over the reals with z3.

    Returns VERIFIED (universally valid), REFUTED (universally false / unsat),
    or None when the claim is contingent, z3 is unavailable, or it cannot be
    translated. None => caller reports UNVERIFIABLE. Never guesses.
    """
    if not _HAS_Z3:
        return None
    try:
        smap = {}
        rel = _z3_rel(lhs_sym, rhs_sym, op, smap)
        s = z3.Solver()
        s.add(z3.Not(rel))
        if s.check() == z3.unsat:      # negation impossible => always true
            return Verdict.VERIFIED
        s2 = z3.Solver()
        s2.add(rel)
        if s2.check() == z3.unsat:     # claim impossible => always false
            return Verdict.REFUTED
        return None                    # contingent — honestly undecided
    except Exception:
        return None


def verify_consistency(claims: List[str]) -> GroundingResult:
    """Check whether a SET of relational claims is jointly satisfiable (z3).

    This catches contradictions no single-claim check can see: a forged thought
    asserting a circular ordering (a > b, b > c, c > a) has three individually
    fine claims but is jointly impossible.

    VERIFIED    = jointly consistent (satisfiable)
    REFUTED     = contradictory (unsatisfiable) — FLAG the thought
    UNVERIFIABLE = fewer than 2 formalizable claims, z3 missing, or untranslatable
    """
    formal = [c for c in claims if _split_comparison(c) is not None]
    joined = " ; ".join(formal)
    if not _HAS_Z3 or not _HAS_SYMPY:
        return GroundingResult(joined, Verdict.UNVERIFIABLE, "z3/sympy unavailable")
    if len(formal) < 2:
        return GroundingResult(joined, Verdict.UNVERIFIABLE, "need >=2 formalizable claims to check consistency")
    try:
        smap = {}
        constraints = []
        for c in formal:
            lhs_s, op, rhs_s = _split_comparison(c)
            constraints.append(_z3_rel(sympify(lhs_s), sympify(rhs_s), op, smap))
        s = z3.Solver()
        s.add(*constraints)
        result = s.check()
    except Exception as e:
        return GroundingResult(joined, Verdict.UNVERIFIABLE, f"could not formalize claim set: {e}")
    if result == z3.unsat:
        return GroundingResult(joined, Verdict.REFUTED, f"z3: the {len(formal)} claims are jointly CONTRADICTORY", method="z3")
    if result == z3.sat:
        return GroundingResult(joined, Verdict.VERIFIED, f"z3: the {len(formal)} claims are jointly consistent", method="z3")
    return GroundingResult(joined, Verdict.UNVERIFIABLE, "z3 returned unknown")


# Conservative claim extraction. An "atom" is a number, a lone (word-bounded)
# variable letter, or an operator/paren — so English words never match: "holds"
# has no word-bounded single letter, but "x" does. An operand is a run of atoms.
# This grabs "2 + 2 = 4" out of "note that 2 + 2 = 4 holds" without swallowing the
# prose. Everything not matched is simply not extracted — never a fabricated claim.
_ATOM = r"(?:\d+\.?\d*|\b[A-Za-z]\b|[-+*/^()])"
_OPERAND = rf"{_ATOM}(?:\s*{_ATOM})*"
_COMPARATOR_ALT = r"==|!=|>=|<=|=|>|<"
_CLAIM_RE = re.compile(rf"{_OPERAND}\s*(?:{_COMPARATOR_ALT})\s*{_OPERAND}")


def extract_claims(text: str) -> List[str]:
    """Pull candidate checkable claims (arithmetic (in)equalities) from text.

    Deliberately conservative: it under-extracts rather than over-extracts. A
    claim it does not recognize is left alone (and will simply not be grounded),
    never coerced into a false positive.
    """
    if not text:
        return []
    out: List[str] = []
    for m in _CLAIM_RE.finditer(text):
        span = m.group(0).strip(" .,:;\n\t")
        if not span:
            continue
        # Keep a span if it's an arithmetic claim (has a digit) OR a comparison
        # (uses an ordering/equality operator, not a bare '='). This admits
        # variable orderings like "a > b" — needed for contradiction detection —
        # while still leaving prose assignments like "set x = y" out of scope.
        has_digit = any(ch.isdigit() for ch in span)
        has_comparison = any(op in span for op in ("==", "!=", ">=", "<=", ">", "<"))
        if has_digit or has_comparison:
            out.append(span)
    return out


def log_shadow(result: GroundingResult, path: str | Path = None) -> None:
    """Append one verdict to the shadow log. SHADOW ONLY — applied is always false.

    Separate from verify() on purpose: verification is pure; persistence is a
    deliberate, opt-in act. Nothing in the runtime calls this until Phase B, and
    even then it only observes. See docs/NEUROSYMBOLIC_GROUNDING.md Phase D.
    """
    path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "grounding_shadow.jsonl"
    rec = result.to_dict()
    rec["mode"] = "shadow"
    rec["applied"] = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # logging must never break a turn
