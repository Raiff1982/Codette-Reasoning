"""Two defects measured live on 2026-08-17, in the middle of a real conversation.

Jonathan was telling her his back hurt at a 7 and radiated down his legs. In
that conversation:

1. **`search_code` ran 667.9 seconds** — eleven minutes, 0.1 tok/s. A direct
   timing test of the old implementation was killed at ten minutes without
   finishing. It called `glob('**/*')` and applied the skip-list per-file,
   AFTER the walk had descended into `.git`, `openvino_backend` (an 8B INT4
   model), `data`, `cocoons` and the archives.

2. **`<tool>empathy</tool>` rendered at the head of her answer**, and a stray
   `; expr = sp.sympify('x + 2*x')")` shipped inside another. The cleanup was
   gated `if has_tool_calls(text)` — so it ran only when the text held a
   *valid* call, and stood down for exactly the malformed leftovers it exists
   to remove.

Both are the same shape as the rest of this repository: a guard that fires when
things are already fine, and a search that cannot say it stopped early.
"""

import time

import pytest

from inference import codette_tools as ct


# ── 1. The search must end, and must say when it stopped short ────────────

def test_search_finishes_fast_on_the_real_tree():
    """The regression itself. Eleven minutes -> a bounded deadline."""
    start = time.monotonic()
    out = ct.tool_search_code("zzz_no_such_string_anywhere_zzz", ".")
    elapsed = time.monotonic() - start
    assert elapsed < ct.SEARCH_DEADLINE_SECONDS + 5, (
        f"search took {elapsed:.1f}s — the deadline is not being honoured")
    assert isinstance(out, str)


def test_a_truncated_search_says_so_and_says_what_it_does_not_mean():
    """Absence must never be indistinguishable from 'we stopped looking'.

    If this line goes missing she reads a partial result as a complete one and
    reasons from 'it is not there'. That is the one-way instrument this
    repository keeps paying for.
    """
    out = ct.tool_search_code("e", ".")           # matches nearly every line
    if "STOPPED EARLY" in out:
        assert "PARTIAL" in out
        assert "not evidence of absence" in out.replace("\n  ", " ")
    else:
        assert "matches in" in out


def test_pruned_directories_are_never_descended(monkeypatch):
    """The actual fix: pruning must happen before the walk descends.

    Asserting on the walk itself rather than on wall-clock, because a fast
    machine could pass a timing test with the old glob still in place.
    """
    seen = []
    real_walk = ct.os.walk

    def spy(top, *a, **k):
        for dirpath, dirnames, filenames in real_walk(top, *a, **k):
            seen.append(dirpath)
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(ct.os, "walk", spy)
    ct.tool_search_code("zzz_no_such_string_zzz", ".")
    bad = [d for d in seen
           if any(part in ct._SEARCH_SKIP_DIRS for part in d.replace("\\", "/").split("/"))]
    assert not bad, f"descended into pruned directories: {bad[:5]}"


def test_search_with_no_pattern_refuses():
    assert "needs a pattern" in ct.tool_search_code("", ".")


# ── 2. The leak, using the exact strings she shipped ──────────────────────

def test_the_perspective_in_tool_tags_is_stripped():
    """Verbatim from the 2026-08-17 transcript, consciousness turn."""
    leaked = "<tool>empathy</tool> It sounds like your pain is radiating"
    out = ct.strip_tool_calls(leaked)
    assert "<tool>" not in out and "</tool>" not in out
    assert "It sounds like your pain is radiating" in out


@pytest.mark.parametrize("closer", ["</bearing>", "</bearig>", "</tool>",
                                    "</ bearing >", "</BEARING>"])
def test_dangling_closers_of_any_tool_name(closer):
    """`</bearig>` truncated a real answer mid-sentence on 2026-08-16."""
    out = ct.strip_tool_calls(f"empathetic connections.{closer}")
    assert closer.strip() not in out
    assert "empathetic connections." in out


@pytest.mark.parametrize("keep", ["</div>", "</span>", "</thinking>", "</p>"])
def test_real_markup_is_left_alone(keep):
    """Bounded on purpose. We remove our litter; we do not edit her prose."""
    out = ct.strip_tool_calls(f"the closing {keep} tag")
    assert keep in out


def test_her_words_survive_the_strip():
    """unwrap, don't delete — the sentence inside was hers and was fine."""
    out = ct.strip_tool_calls(
        '<bearing>"I\'m listening with my full architecture"</bearing>')
    assert "listening with my full architecture" in out
    assert "<bearing>" not in out


def test_clean_prose_is_untouched():
    """The strip must be safe to run unconditionally — that is the whole fix."""
    prose = ("Your back hurts again today, and it's affecting you. "
             "Can you tell me more about what's going on?")
    assert ct.strip_tool_calls(prose) == prose


def test_strip_runs_even_when_there_is_no_valid_call():
    """The root cause, stated as a test.

    `has_tool_calls` is False for this string — `empathy` is a perspective with
    no args, not a tool. Under the old gate the cleanup never ran and this
    rendered to Jonathan verbatim.
    """
    leaked = "<tool>empathy</tool> It sounds like"
    assert not ct.has_tool_calls(leaked), (
        "premise changed: this string now parses as a call, "
        "so this test no longer covers the ungated path")
    assert "<tool>" not in ct.strip_tool_calls(leaked)


def test_the_dangling_name_list_comes_from_the_registry():
    """Not a copy. Two bugs in this file already came from a drifted copy."""
    names = ct._TOOL_TAG_NAMES()
    assert "bearing" in names and "scratch_write" in names
    assert ct._dangling_closer_re().search("</scratch_write>")
