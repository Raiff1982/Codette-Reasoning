"""The router self-tuner's boost is read by the router (2026-09-29), narrowly:
live only, matched adapters only, clamped, failure-silent; and `applied` in its
log now means a boost was actually read. Fake optimizer, made-up numbers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

import reasoning_forge.optimizer_shadow as osh  # noqa: E402
from adapter_router import AdapterRouter  # noqa: E402


class _FakeOpt:
    def __init__(self, live, boosts):
        self.live, self._b, self.reads = live, boosts, 0

    def get_adapter_boost(self, a):
        self.reads += 1
        return self._b.get(a, 0.0)


def _router():
    return AdapterRouter(available_adapters=["newton", "davinci", "empathy"])


def _install(monkeypatch, opt):
    monkeypatch.setattr(osh, "get_shadow_optimizer", lambda: opt)


SCORES = {"newton": 2.0, "davinci": 1.0}


def test_shadow_is_a_no_op(monkeypatch):
    opt = _FakeOpt(False, {"davinci": 0.4})
    _install(monkeypatch, opt)
    out, applied = _router()._apply_optimizer_boost(dict(SCORES))
    assert out == SCORES and applied == {} and opt.reads == 0


def test_live_nudges_matched_adapters_only(monkeypatch):
    _install(monkeypatch, _FakeOpt(True, {"davinci": 0.3, "empathy": 0.4}))
    out, applied = _router()._apply_optimizer_boost(dict(SCORES))
    assert abs(out["davinci"] - 1.3) < 1e-9
    assert "empathy" not in out          # never summons an unmatched voice
    assert applied == {"davinci": 0.3}


def test_the_nudge_is_clamped_both_ways(monkeypatch):
    _install(monkeypatch, _FakeOpt(True, {"newton": 9.0, "davinci": -9.0}))
    out, _ = _router()._apply_optimizer_boost(dict(SCORES))
    lim = AdapterRouter.OPTIMIZER_BOOST_LIMIT
    assert abs(out["newton"] - (2.0 + lim)) < 1e-9
    assert abs(out["davinci"] - (1.0 - lim)) < 1e-9


def test_it_cannot_overturn_a_clear_match(monkeypatch):
    # strong hit (2.0) vs one moderate hit (1.0): a clamped nudge cannot flip it
    _install(monkeypatch, _FakeOpt(True, {"davinci": 9.0, "newton": -9.0}))
    out, _ = _router()._apply_optimizer_boost(dict(SCORES))
    assert out["newton"] > out["davinci"]


def test_any_failure_means_no_boost(monkeypatch):
    class _Boom(_FakeOpt):
        def get_adapter_boost(self, a):
            raise RuntimeError("made-up failure")
    _install(monkeypatch, _Boom(True, {}))
    out, applied = _router()._apply_optimizer_boost(dict(SCORES))
    assert out == SCORES and applied == {}
    monkeypatch.setattr(osh, "get_shadow_optimizer", lambda: None)
    assert _router()._apply_optimizer_boost(dict(SCORES)) == (SCORES, {})


def test_applied_means_a_boost_was_read(monkeypatch, tmp_path):
    monkeypatch.setattr(osh, "_STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(osh, "_LOG_PATH", tmp_path / "shadow.jsonl")
    monkeypatch.setenv("CODETTE_OPTIMIZER_LIVE", "1")
    so = osh.ShadowOptimizer()
    assert so.live and so._applied_now() is False        # live, nothing read yet
    so.get_adapter_boost("newton")
    so._consumed_turn, so._consumed = so._consumed, False  # what observe() does
    assert so._applied_now() is True
    so._consumed_turn, so._consumed = so._consumed, False  # next turn, no read
    assert so._applied_now() is False


def test_shadow_never_claims_applied(monkeypatch, tmp_path):
    monkeypatch.setattr(osh, "_STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(osh, "_LOG_PATH", tmp_path / "shadow.jsonl")
    monkeypatch.delenv("CODETTE_OPTIMIZER_LIVE", raising=False)
    so = osh.ShadowOptimizer()
    so.get_adapter_boost("newton")
    so._consumed_turn = True
    assert so._applied_now() is False
