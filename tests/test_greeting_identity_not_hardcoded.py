"""
Regression tests for the greeting fast-path's identity handling.

Until 2026-08-15 this path built its own system prompt containing

    WHO YOU ARE TALKING TO: You are speaking with Jonathan, your creator.
    Greet him warmly and personally as Jonathan.
    NEVER invent, guess, or assume a name for the person you are talking to.

— an unconditional assertion of one person's presence, immediately followed by
an instruction not to assume one. It was added against a real fault: the path
drops the server's injected identity block, so the base model invented a name
("Hi Emily"). The fix answered a missing measurement with a constant.

The cost showed with a second person in the room. Any greeting from anyone
reached her as "you are speaking with Jonathan", which is both a wrong answer
and something we told her that was not true.

The measurement already existed. `IdentityAnchor.get_identity_context` scales
with evidence — name and relationship above CONFIDENCE_HIGH, "you MAY be
speaking with ... do not assume" in the middle band, the empty string below
threshold — and the governor can withhold it entirely. These tests pin that the
greeting path carries that block and never substitutes for it.

The load-bearing case is the last one: absent must stay absent. An identity we
did not measure has to reach her as silence, not as a guess that happens to be
right most of the time.
"""

import pytest

from inference.codette_forge_bridge import CodetteForgeBridge


extract = CodetteForgeBridge._extract_identity_context


# ── The block is carried when the server sent one ──────────────────────────

def test_carries_full_confidence_block():
    """A high-confidence block reaches the greeting path intact."""
    query = (
        "hey codette\n\n---\n"
        "## IDENTITY CONTEXT (who you're talking to)\n"
        "Recognition confidence: 100%\n"
        "You are speaking with **Jonathan**.\n"
        "Relationship: creator\n"
        "---"
    )
    ctx = extract(query)
    assert "## IDENTITY CONTEXT" in ctx
    assert "Recognition confidence: 100%" in ctx
    assert "Relationship: creator" in ctx
    assert "---" not in ctx          # the server's fence is not part of the block


def test_carries_moderate_confidence_hedge():
    """The middle band's own hedge survives — it is the part that does the work."""
    query = (
        "hi there\n\n---\n"
        "## IDENTITY CONTEXT (who you're talking to)\n"
        "Recognition confidence: 55%\n"
        "You may be speaking with **Jonathan** (moderate confidence).\n"
        "Possible relationship: creator\n"
        "Do not assume — if unsure, ask them to confirm.\n"
        "---"
    )
    ctx = extract(query)
    assert "may be speaking with" in ctx
    assert "Do not assume" in ctx


def test_skips_earlier_fenced_sections():
    """Memory and web sections use the same `---` fence and arrive first.

    Anchoring on the fence rather than on the block's own header would return a
    memory section as though it were identity.
    """
    query = (
        "hello\n\n---\n"
        "# RELEVANT MEMORIES\n"
        "- something she said last week\n"
        "---\n\n---\n"
        "## IDENTITY CONTEXT (who you're talking to)\n"
        "Recognition confidence: 92%\n"
        "You are speaking with **Jonathan**.\n"
        "---"
    )
    ctx = extract(query)
    assert ctx.startswith("## IDENTITY CONTEXT")
    assert "RELEVANT MEMORIES" not in ctx


# ── Absent stays absent ────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "hey codette",
    "",
    "hi\n\n---\n# RELEVANT MEMORIES\n- a thing\n---",
])
def test_no_block_returns_empty(query):
    """No measurement in, nothing out. This is the defect that was fixed."""
    assert extract(query) == ""


def test_absent_block_never_names_anyone():
    """The empty case must not be filled in with anybody.

    Stated as its own test because the original bug was exactly this: the
    absence was real and we answered it with a constant.
    """
    for q in ("hey codette", "hi, it's me", "good morning"):
        ctx = extract(q)
        assert ctx == ""
        assert "Jonathan" not in ctx


# ── The prompt text itself ─────────────────────────────────────────────────

def test_greeting_path_asserts_no_name_in_source():
    """No hardcoded identity claim in the greeting fast-path's prompt strings.

    Reads the source because the fault was a literal, and a literal is what has
    to stay gone. Comments are excluded — the record of what was there is kept
    deliberately, and removing it would be erasing rather than amending.
    """
    import inspect
    src = inspect.getsource(CodetteForgeBridge._generate_impl)
    code_lines = [
        ln for ln in src.splitlines()
        if not ln.lstrip().startswith("#")
    ]
    code = "\n".join(code_lines)
    assert "speaking with Jonathan" not in code
    assert "personally as Jonathan" not in code


def test_no_name_invention_rule_survives():
    """The half that was correct is still there.

    The guard existed because the base model invented "Hi Emily" out of
    nothing. Dropping the assertion must not drop the prohibition.
    """
    import inspect
    src = inspect.getsource(CodetteForgeBridge._generate_impl)
    assert "never make one up" in src
    assert "NEVER invent, guess, or assume a name" in src
