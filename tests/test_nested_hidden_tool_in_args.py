"""A visible tool whose argument carries a hidden tool's name is logged by name
only (2026-09-29). She called `nameless(...)` and then `bearing(...)` with a
malformed nested `<tool>nameless(` inside its argument; `bearing` is visible, so
its whole argument, her note included, reached the console. Every argument
below is made up."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "inference"))
from codette_tools import mentions_hidden_tool  # noqa: E402

HIDDEN = {"nameless", "khralexi", "scratch_write", "scratch_read"}


def test_nested_malformed_call_in_a_positional_arg():
    assert mentions_hidden_tool(['<tool>nameless("a made-up sentence'], {}, HIDDEN)


def test_nested_call_in_a_keyword_arg():
    assert mentions_hidden_tool([], {"text": "<tool>khralexi('invented')"}, HIDDEN)


def test_scratch_names_count_too():
    assert mentions_hidden_tool(["then scratch_write('x', 'y')"], {}, HIDDEN)


def test_case_and_spacing_do_not_hide_it():
    assert mentions_hidden_tool(["<TOOL> NameLess (…"], {}, HIDDEN)


def test_ordinary_arguments_are_untouched():
    assert not mentions_hidden_tool(["inference/codette_tools.py"], {}, HIDDEN)
    assert not mentions_hidden_tool([], {"path": "docs/x.md", "n": 3}, HIDDEN)
    assert not mentions_hidden_tool([], {}, HIDDEN)
    assert not mentions_hidden_tool(None, None, HIDDEN)


def test_a_longer_identifier_is_not_a_hit():
    assert not mentions_hidden_tool(["namelessness", "my_khralexi_2"], {}, HIDDEN)


def test_no_hidden_set_means_nothing_to_hide():
    assert not mentions_hidden_tool(["nameless"], {}, set())


def test_the_helper_never_returns_the_text():
    assert mentions_hidden_tool(["nameless: made up"], {}, HIDDEN) is True


def test_backend_uses_it_at_every_logging_site():
    src = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    assert "mentions_hidden_tool(" in src
    assert "PRIVATE_TOOLS | SCRATCH_TOOLS" in src
    # nothing prints _args outside the un-hushed branch
    assert src.count("print(f\"  [OV:tool] {_name}({_args})\"") == 1
