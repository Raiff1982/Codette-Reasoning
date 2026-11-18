"""forge_with_debate must reach its memory store and its adaptive synthesis.

Until 2026-11-18 both read `analyses` (and the store also `epistemic_report`
and `safety_notes`), names that exist only in _forge_single_safe. The NameError
was caught and logged at DEBUG, so this path never stored a memory.
"""
import logging


class _Orch:
    def route_and_generate(self, q, **kw):
        return {"response": "Privacy and safety trade off; a layered design limits each harm.",
                "adapter": "mock", "tokens": 12}


def test_forge_with_debate_stores_and_synthesises(caplog):
    from reasoning_forge.forge_engine import ForgeEngine
    caplog.set_level(logging.DEBUG, logger="reasoning_forge")
    ForgeEngine(orchestrator=_Orch()).forge_with_debate(
        "How should privacy and safety be balanced in surveillance?")
    text = caplog.text
    assert "is not defined" not in text
    assert "Memory storage failed" not in text
