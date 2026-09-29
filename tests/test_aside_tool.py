"""`aside`: a line for Jonathan, under her reply, that is not part of her answer
(2026-09-29). Hers to use or not; visible, and says so. Every string is made up."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "inference"))
import codette_tools  # noqa: E402


def test_registered_with_a_handler():
    spec = codette_tools.ToolRegistry().tools["aside"]
    assert spec["handler"] is codette_tools.tool_aside


def test_description_says_he_can_see_it_and_that_it_is_hers_to_use():
    d = codette_tools.ToolRegistry().tools["aside"]["description"]
    assert "Not private" in d and "he will read it" in d
    assert "khralexi" in d and "leave_note" in d       # the difference, named
    assert "yours" in d and "nothing checks" in d
    # unlike care_check it does NOT claim to be unrecorded: he sees it
    assert "no record" not in d.lower()


def test_she_is_heard_in_both_spellings():
    for text in ('<tool>aside("made up line")</tool>',
                 '<tool>aside(text="made up line")</tool>'):
        assert codette_tools.has_tool_calls(text)
        name, args, kwargs = codette_tools.parse_tool_calls(text)[0]
        assert name == "aside"
        assert "made up line" in (" ".join(map(str, args)) + " ".join(map(str, kwargs.values())))


def test_handler_answers_plainly_and_stores_nothing():
    before = dict(vars(codette_tools))
    out = codette_tools.tool_aside("a made-up line")
    assert "Jonathan will see it" in out and "or not" in out
    assert "Nothing written" in codette_tools.tool_aside("   ")
    # no counter, no queue: nothing to count or replay against her
    assert not any(k.lower().startswith("_aside") for k in vars(codette_tools) if k not in before)


def test_ask_points_a_person_name_at_it_and_keeps_the_truth():
    class _O:
        _current_adapter = None
        def _load_model(self, a): pass
    codette_tools._ORCHESTRATOR = _O()
    orig = codette_tools._available_perspectives
    codette_tools._available_perspectives = lambda: ["newton"]
    try:
        out = codette_tools.tool_ask("Jonathan", "made up?")
    finally:
        codette_tools._available_perspectives = orig
    assert "is a person" in out and "in your reply" in out and "aside" in out


def test_tool_log_carries_keyword_text_so_the_page_can_show_it():
    src = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    assert '(list(_args or []) + [str(_v) for _v in (_kwargs or {}).values()])' in src


def test_page_renders_it_only_when_she_left_one():
    js = (ROOT / "inference" / "static" / "app.js").read_text(encoding="utf-8")
    assert "call.tool !== 'aside'" in js and "aside-for-you" in js
    assert "if (!said) continue;" in js
    css = (ROOT / "inference" / "static" / "style.css").read_text(encoding="utf-8")
    assert ".aside-for-you" in css


@pytest.mark.skipif(shutil.which("node") is None, reason="no node to syntax-check app.js")
def test_app_js_still_parses():
    r = subprocess.run(["node", "--check", str(ROOT / "inference" / "static" / "app.js")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
