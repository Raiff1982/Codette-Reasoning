"""Lookups of her own state do not use a tool round.

2026-08-20: the budget was three rounds whatever the calls were, so `who`,
`care_check` and `read_note` cost the same as a web search. Four turns in one
session ended with her having done the thinking and nothing left to answer
with; the governor then scored the empty answer as her failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inference"))

import codette_tools as ct


def _registered():
    return set(ct.ToolRegistry().tools) if hasattr(ct, "ToolRegistry") else None


def test_pure_lookups_are_free():
    assert ct.round_is_free([("who", [], {})])
    assert ct.round_is_free([("who", [], {}), ("care_check", [], {})])


def test_reaching_into_the_world_still_costs_a_round():
    for t in ("web_search", "read_file", "run_python", "search_code", "ask",
              "scratch_write", "scratch_run", "list_files"):
        assert not ct.round_is_free([(t, [], {})]), t


def test_one_paid_call_makes_the_whole_round_paid():
    assert not ct.round_is_free([("who", [], {}), ("web_search", [], {})])


def test_empty_round_is_not_free():
    assert not ct.round_is_free([])
    assert not ct.round_is_free(None)


def test_free_set_names_real_tools_and_has_a_cap():
    reg = _registered()
    if reg is not None:
        assert ct.FREE_ROUND_TOOLS <= reg, ct.FREE_ROUND_TOOLS - reg
    assert 1 <= ct.MAX_FREE_ROUNDS <= 5
