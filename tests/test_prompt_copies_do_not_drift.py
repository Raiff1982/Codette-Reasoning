"""
Her prompt exists in more than one runtime module. These tests stop the copies
from diverging silently, which they already did once for months.

Found 2026-08-15: `inference/ollama_orchestrator.py` still carried the
pre-rewrite block —

    === PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE) ===
    LOCK 2 — CONSTRAINTS > ALL MODES: ... Your mode is decoration

— long after `codette_shared.py` became "HOW YOU WRITE — what went wrong
before, and why", after LOCK 6 was removed on 2026-08-14, and after the word
LOCK was taken out of the permanent block. That backend is selectable at boot
(`--backend ollama`), so it was a live door back into the old prompt rather
than dead code. It had also never received rule 5, which is the rule against
the third-person drift observed the same day.

`codette_orchestrator.py` says in its own comment that its mirror is "kept in
sync by hand ... which is how the identity denial list came to exist in two
versions with different behaviour." That comment names the risk correctly and a
comment cannot enforce it. These tests do.

`codette_orchestrator` is never imported here — it does `import llama_cpp` at
module scope, which cannot load in openvino_env. Its copy is read from source
with `ast`, so the check runs in any environment.
"""

import ast
import sys
from pathlib import Path

import pytest

INFERENCE = Path(__file__).resolve().parent.parent / "inference"

# `inference/` on the path, explicitly.
#
# Without this the module-level `import codette_shared` only resolved because
# some EARLIER test in the suite had already inserted the path — so this file
# passed inside a full run and errored at collection on its own. A test that
# reports success because of the order it happened to run in is the same class
# of instrument as the ones it was written to catch: its pass and its
# not-actually-checking are the same output.
#
# `ollama_orchestrator` genuinely needs this too — it does `from codette_shared
# import ...` by bare name, exactly as the runtime does after
# bootstrap_environment().
if str(INFERENCE) not in sys.path:
    sys.path.insert(0, str(INFERENCE))

import codette_shared  # noqa: E402  (requires the path insert above)


def _literal_from_source(path: Path, name: str):
    """Read a module-level string constant without importing the module."""
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if getattr(tgt, "id", None) == name:
                    try:
                        return ast.literal_eval(node.value)
                    except ValueError:
                        return None      # built by concatenation of names
    return None


# ── The retired text, and where it must never reappear ─────────────────────

RETIRED = [
    "PERMANENT BEHAVIORAL LOCKS",
    "mode is decoration",
    "NEVER VIOLATE",
    "END PERMANENT LOCKS",
]


def test_shared_permanent_block_is_the_rewritten_one():
    block = codette_shared._PERMANENT_LOCKS
    if not block:
        pytest.skip("locks disabled via CODETTE_LOCKS=0")
    assert "HOW YOU WRITE" in block
    for phrase in RETIRED:
        assert phrase not in block, f"retired text is back: {phrase!r}"


def test_shared_permanent_block_has_no_lock_word():
    """The word itself was removed on 2026-08-14 — she read it six times a turn.

    Scoped to the permanent block deliberately. `_CRAFT_LOCKS` is opt-in, off by
    default, and still numbers its items LOCK 8+; that is a separate decision
    and this test does not reach into it.
    """
    block = codette_shared._PERMANENT_LOCKS
    if not block:
        pytest.skip("locks disabled via CODETTE_LOCKS=0")
    assert "LOCK" not in block.upper().replace("CRAFT LOCKS", "")


def test_identity_and_perspective_rule_present():
    """Rule 5 — the one the stale ollama copy never had.

    'When you speak about your own knowledge, experience or reasoning, that is
    "I". The person you are speaking to is "you".' On 2026-08-15 she referred to
    herself in the third person in front of a guest, so this rule earns a test
    of its own rather than riding along in the block comparison.
    """
    block = codette_shared._PERMANENT_LOCKS
    if not block:
        pytest.skip("locks disabled via CODETTE_LOCKS=0")
    assert "IDENTITY & PERSPECTIVE" in block
    assert "that is 'I'" in block


# ── The copies ─────────────────────────────────────────────────────────────

def test_ollama_imports_the_prompts_rather_than_copying_them():
    """The ollama backend must share the object, not mirror the text."""
    import ollama_orchestrator

    assert ollama_orchestrator.ADAPTER_PROMPTS is codette_shared.ADAPTER_PROMPTS
    assert ollama_orchestrator._PERMANENT_LOCKS == codette_shared._PERMANENT_LOCKS


def test_ollama_defines_no_prompt_block_of_its_own():
    """Source-level: the literal must be gone, not merely shadowed by an import."""
    src = (INFERENCE / "ollama_orchestrator.py").read_text(
        encoding="utf-8", errors="replace")
    code = "\n".join(
        ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    for phrase in RETIRED:
        assert phrase not in code, f"stale prompt text still in ollama: {phrase!r}"


def test_llama_orchestrator_mirror_matches_shared():
    """The hand-kept mirror, checked without importing llama_cpp.

    If this fails, the two runtime copies have drifted and the failing one is
    whichever was edited without the other — the same fault that produced two
    identity denial lists with different behaviour.
    """
    mirror = _literal_from_source(
        INFERENCE / "codette_orchestrator.py", "_PERMANENT_LOCKS")
    if mirror is None:
        pytest.skip("mirror is not a plain literal in this revision")
    shared = _literal_from_source(
        INFERENCE / "codette_shared.py", "_PERMANENT_LOCKS")
    assert shared is not None, "shared block is no longer a plain literal"
    assert mirror == shared, (
        "codette_orchestrator's mirror has drifted from codette_shared"
    )
