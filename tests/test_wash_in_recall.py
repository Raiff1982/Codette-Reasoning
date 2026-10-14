"""lexical_whitening in recall: demotion-only, off-switchable, and never fatal."""
import reasoning_forge.unified_memory as um
from reasoning_forge.unified_memory import UnifiedMemory

FILLER = ("Where these converge the correct answer is clear. Competing analytical "
          "frames remain open and pull in different directions, both frames stay "
          "open as the tensions remain unresolved for now.")


def _mem(tmp_path, n_filler=70, monkeypatch=None):
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    m = UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)
    for i in range(n_filler):
        m.store(f"question number {i} about topic{i}", FILLER, adapter="empathy")
    m.store("what is the boiling point of water on mount everest",
            "On Everest the air pressure is about a third of sea level, so water "
            "boils near 70 degrees Celsius, which is why tea made there is poor.",
            adapter="empathy")
    return m


def test_repeated_filler_is_demoted_and_specific_content_is_not(tmp_path, monkeypatch):
    monkeypatch.setattr(um, "WASH_MIN_DOCS", 50)     # 70 docs here; 300 in production
    m = _mem(tmp_path)
    filler = {"response": FILLER, "adapter": "empathy"}
    specific = {"response": "On Everest the air pressure is about a third of sea "
                            "level, so water boils near 70 degrees Celsius, which "
                            "is why tea made there is poor.", "adapter": "empathy"}
    assert m._wash_for(filler) < 1.0
    assert m._wash_for(specific) == 1.0


def test_it_only_ever_demotes(tmp_path, monkeypatch):
    monkeypatch.setattr(um, "WASH_MIN_DOCS", 50)
    m = _mem(tmp_path)
    for text in (FILLER, "short", "x " * 80, "Water boils at one hundred degrees at sea level, a fact of pressure."):
        w = m._wash_for({"response": text, "adapter": "empathy"})
        assert 0.0 < w <= 1.0


def test_kill_switch_restores_unwashed_ranking(tmp_path, monkeypatch):
    monkeypatch.setattr(um, "WASH_MIN_DOCS", 50)
    m = _mem(tmp_path)
    monkeypatch.setenv("CODETTE_WASH_RECALL", "0")
    assert m._wash_for({"response": FILLER, "adapter": "empathy"}) == 1.0


def test_a_failing_wash_demotes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(um, "WASH_MIN_DOCS", 50)
    m = _mem(tmp_path)
    import reasoning_forge.lexical_whitening as lw
    monkeypatch.setattr(lw.CorpusProfile, "build", classmethod(lambda cls, *a, **k: 1 / 0))
    m._wash_profile = None
    assert m._wash_for({"response": FILLER, "adapter": "empathy"}) == 1.0


def test_recall_still_finds_the_specific_answer(tmp_path):
    m = _mem(tmp_path)
    got = m.recall_relevant("boiling point of water on mount everest", max_results=3)
    assert got and "Everest" in got[0]["response"]


def test_a_small_store_is_never_washed(tmp_path):
    """Below WASH_MIN_DOCS the prevalence threshold is meaningless: 1 of 41 is 2.4%."""
    m = _mem(tmp_path, n_filler=40)
    assert m._wash_for({"response": FILLER, "adapter": "empathy"}) == 1.0
    assert m._wash_for({"response": "On Everest the air pressure is about a third "
                        "of sea level so water boils near seventy degrees Celsius.",
                        "adapter": "empathy"}) == 1.0
