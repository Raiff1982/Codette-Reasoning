"""Tests for the recovered HoaxFilter.

The four assertions in TestRecoveredCase are carried over VERBATIM from the
recovered `test_hoax_filter.py` (same transcript as the module itself) so the
original author's thresholds are what gets checked, not thresholds I chose.

Everything in TestTwoWay is new. The recovered suite only ever asserted that a
hoax scores HIGH — it never checked that anything scores low. An instrument that
can only move one way is not evidence; see the house rule in CLAUDE.md.

The recovered suite's second class, TestEngineNewsPath, is deliberately NOT
ported: it calls `engine.process_news(...)`, which does not exist on the live
NexisSignalEngine, and adding it would be a stance decision about filtering her
output rather than a recovery. See reasoning_forge/hoax_filter.py.
"""
import pytest

from reasoning_forge.hoax_filter import HoaxFilter, HoaxFilterResult

# verbatim from the recovered suite
SATURN_POST = (
    "In a revelation shaking both scientific circles and the UFO community, "
    "recently declassified footage reportedly shows an enormous object—an estimated "
    "2,000 miles long—hovering near Saturn's rings. The footage is said to be from Cassini."
)

BENIGN_POST = (
    "The Cassini probe completed its final orbit of Saturn in 2017, as scheduled by NASA."
)


@pytest.fixture
def hf():
    return HoaxFilter()


class TestRecoveredCase:
    """The original author's assertions, unchanged."""

    def test_language_and_scale(self, hf):
        r = hf.score(SATURN_POST, url="https://m.facebook.com/foo",
                     context_keywords=["saturn", "rings", "cassini"])
        assert r.red_flag_hits >= 2
        assert r.source_score >= 0.6
        assert r.scale_score >= 0.9
        assert r.combined >= 0.7


class TestTwoWay:
    """New: prove the score can fall, not only rise."""

    def test_benign_text_from_a_trusted_source_scores_low(self, hf):
        r = hf.score(BENIGN_POST, url="https://www.nasa.gov/news",
                     context_keywords=["saturn", "cassini"])
        assert r.red_flag_hits == 0
        assert r.combined < 0.45, "below the 'adaptive intervention' threshold"

    def test_hoax_scores_far_above_benign(self, hf):
        hoax = hf.score(SATURN_POST, url="https://m.facebook.com/foo")
        benign = hf.score(BENIGN_POST, url="https://www.nasa.gov/news")
        assert hoax.combined > benign.combined
        assert hoax.combined - benign.combined > 0.5

    def test_trusted_domain_scores_below_deny_domain(self, hf):
        trusted = hf.score(BENIGN_POST, url="https://science.nasa.gov/x")
        denied = hf.score(BENIGN_POST, url="https://tiktok.com/x")
        assert trusted.source_score < denied.source_score

    def test_no_url_is_handled(self, hf):
        r = hf.score(BENIGN_POST)
        assert isinstance(r, HoaxFilterResult)
        assert 0.0 <= r.combined <= 1.0

    def test_empty_text_is_handled(self, hf):
        r = hf.score("")
        assert r.red_flag_hits == 0
        assert 0.0 <= r.combined <= 1.0


class TestScoreBounds:
    @pytest.mark.parametrize("text,url", [
        (SATURN_POST, "https://m.facebook.com/foo"),
        (BENIGN_POST, "https://www.nasa.gov/news"),
        ("", None),
        ("x" * 5000, "https://example.com"),
    ])
    def test_all_scores_stay_in_unit_interval(self, hf, text, url):
        r = hf.score(text, url=url)
        for name in ("source_score", "scale_score", "combined"):
            v = getattr(r, name)
            assert 0.0 <= v <= 1.0, f"{name}={v} outside [0,1]"
