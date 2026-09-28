#!/usr/bin/env python3
"""Tests for the engagement outcome signal.

The point of these is not coverage for its own sake. A miscalibrated engagement
signal is worse than no signal: it would feed the optimizer a reward that is
inverted (chasing a bad answer scores as success) or fabricated (silence scored
as failure). So the abstention cases are tested as hard as the positive ones.
"""
import unittest

from reasoning_forge.engagement_signal import (
    push_off,
    classify_from_history,
    classify_engagement,
    RE_ASK_THRESHOLD,
    UPTAKE_THRESHOLD,
)


class TestNegativeEvidence(unittest.TestCase):
    """Cases where the answer demonstrably did not land."""

    def test_explicit_correction_is_negative(self):
        r = classify_engagement(
            "What is the capital of Australia?",
            "The capital of Australia is Sydney, the largest city.",
            "No, that's wrong — it's Canberra.",
        )
        self.assertIs(r.value, False)
        self.assertIn("corrects", r.reason)

    def test_not_what_i_asked_is_negative(self):
        r = classify_engagement(
            "How do I reset the optimizer state?",
            "The optimizer uses a stochastic hill-climber with temperature decay.",
            "That's not what I asked about.",
        )
        self.assertIs(r.value, False)

    def test_re_ask_is_negative(self):
        r = classify_engagement(
            "How does the drift detector compute epsilon slope?",
            "It examines cocoons and produces a report.",
            "How does the drift detector compute the epsilon slope?",
        )
        self.assertIs(r.value, False)
        self.assertIn("re-asks", r.reason)

    def test_re_ask_beats_incidental_uptake(self):
        """A correction that quotes the answer is still a correction.

        Negative evidence is checked first precisely because rejections tend to
        repeat the wording they are rejecting, which would otherwise register
        as uptake and score positive.
        """
        r = classify_engagement(
            "What is the capital of Australia?",
            "The capital of Australia is Sydney.",
            "No — Sydney is not the capital of Australia.",
        )
        self.assertIs(r.value, False)


class TestPositiveEvidence(unittest.TestCase):
    """Cases where the follow-up demonstrably picked something up."""

    def test_follow_up_building_on_answer_is_positive(self):
        r = classify_engagement(
            "Why is the optimizer not going live?",
            "Because user_continued is never measured, so the reward has no "
            "outcome term and consists only of coherence and tension proxies.",
            "How would we measure that outcome term properly?",
        )
        self.assertIs(r.value, True)
        self.assertIn("builds on", r.reason)

    def test_uptake_uses_response_not_question(self):
        """Uptake must come from the RESPONSE, not from restating the question.

        This is the distinction that separates 'engaged with the answer' from
        'still circling the original topic', and it is the whole basis for
        claiming the signal measures the answer at all.
        """
        r = classify_engagement(
            "Tell me about the memory kernel.",
            "The memory kernel anchors entries with SHA256 and applies "
            "importance decay over time.",
            "What happens to importance decay when entries are anchored?",
        )
        self.assertIs(r.value, True)


class TestAbstention(unittest.TestCase):
    """Cases where the honest answer is 'not measured'.

    Every one of these would be a fabricated measurement if forced to a
    boolean, which is the invariant the optimizer's reward depends on.
    """

    def test_session_end_is_not_failure(self):
        """Silence is not a verdict — the user may have got what they needed."""
        r = classify_engagement("q", "a substantive answer here", "")
        self.assertIsNone(r.value)
        self.assertFalse(r.measured)

    def test_bare_acknowledgement_is_uninformative(self):
        for ack in ("ok", "thanks", "Got it.", "great", "yep"):
            with self.subTest(ack=ack):
                r = classify_engagement(
                    "What is the tension threshold?",
                    "It defaults to 0.15 and bounds the contraction ratio.",
                    ack,
                )
                self.assertIsNone(r.value, f"{ack!r} should not be scored")

    def test_topic_change_is_not_evidence(self):
        r = classify_engagement(
            "What is the tension threshold?",
            "It defaults to 0.15 and bounds the contraction ratio.",
            "Separately, can you look at the Dockerfile permissions?",
        )
        self.assertIsNone(r.value)
        self.assertIn("topic change", r.reason)

    def test_no_previous_turn(self):
        r = classify_engagement("", "", "first question of the session")
        self.assertIsNone(r.value)

    def test_thanks_is_not_scored_as_success(self):
        """Politeness is not evidence the content was any use.

        Scoring "thanks" as success is how a system learns to optimise for
        being thanked rather than for being right.
        """
        r = classify_engagement(
            "Explain the decay term.",
            "Every boost fades 10% per step and must be re-earned.",
            "thanks!",
        )
        self.assertIsNone(r.value)


class TestInvertedSignalGuard(unittest.TestCase):
    """The specific failure this classifier exists to prevent."""

    def test_chasing_a_bad_answer_does_not_score_as_success(self):
        """A user forced to re-ask must never register as engagement.

        This is the whole reason the naive 'they sent another message'
        heuristic was rejected: it rewards answers that need chasing and
        punishes answers good enough to end the exchange.
        """
        bad = classify_engagement(
            "What is the capital of Australia?",
            "Australia is a country in the southern hemisphere.",
            "What is the capital of Australia?",
        )
        good = classify_engagement(
            "What is the capital of Australia?",
            "Canberra is the capital of Australia.",
            "",  # satisfied, conversation ends
        )
        self.assertIs(bad.value, False, "chasing must not score positive")
        self.assertIsNone(good.value, "a satisfied exit must not score negative")
        # And the inversion must not happen: bad must never outrank good.
        self.assertNotEqual(bad.value, True)


class TestPushOff(unittest.TestCase):
    """The forward half: the wall is where the push comes from.

    Reading the follow-up only backwards (scoring the turn that ended) discards
    the half of the information that points at what to do next. These assert
    that the same classification steers the CURRENT turn.
    """

    def _hint(self, prev_q, prev_r, next_q, adapter="philosophy"):
        return push_off(classify_engagement(prev_q, prev_r, next_q), adapter)

    def test_failed_answer_steers_away(self):
        h = self._hint(
            "What is the capital of Australia?",
            "The capital of Australia is Sydney.",
            "No, that's wrong — it's Canberra.",
        )
        self.assertEqual(h["steer"], "diverge")
        self.assertEqual(h["avoid_adapter"], "philosophy")
        self.assertTrue(h["widen_perspectives"])
        self.assertGreater(h["confidence"], 0.0)

    def test_landed_answer_keeps_the_approach(self):
        h = self._hint(
            "Why won't the optimizer go live?",
            "Because user_continued is never measured, so the reward has no "
            "outcome term at all.",
            "How would we measure that outcome term?",
        )
        self.assertEqual(h["steer"], "continue")
        self.assertEqual(h["prefer_adapter"], "philosophy")
        self.assertFalse(h["widen_perspectives"])

    def test_abstention_produces_no_steer(self):
        """Absence of evidence must not become a steer.

        Same rule as the reward: if the classifier abstained, nothing is
        claimed and nothing is nudged. A hint with confidence 0.0 is inert.
        """
        for follow_up in ("thanks", "", "Separately, check the Dockerfile."):
            with self.subTest(follow_up=follow_up):
                h = self._hint(
                    "What is the tension threshold?",
                    "It defaults to 0.15 and bounds the contraction ratio.",
                    follow_up,
                )
                self.assertEqual(h["steer"], "none")
                self.assertEqual(h["confidence"], 0.0)
                self.assertFalse(h["widen_perspectives"])

    def test_correction_is_more_confident_than_a_re_ask(self):
        """An explicit rejection is stronger evidence than a repeated question."""
        correction = self._hint(
            "What is the capital of Australia?",
            "The capital of Australia is Sydney.",
            "No, that's wrong.",
        )
        re_ask = self._hint(
            "How does the drift detector compute epsilon slope?",
            "It examines cocoons and produces a report.",
            "How does the drift detector compute the epsilon slope?",
        )
        self.assertEqual(correction["steer"], "diverge")
        self.assertEqual(re_ask["steer"], "diverge")
        self.assertGreater(correction["confidence"], re_ask["confidence"])


class TestRewardIntegration(unittest.TestCase):
    """The signal must actually move the optimizer's reward, and in the right
    direction — otherwise it is decoration."""

    def _q(self, user_continued):
        import time
        from reasoning_forge.quantum_optimizer import QuantumOptimizer, QualitySignal
        opt = QuantumOptimizer()
        return opt._compute_quality(QualitySignal(
            timestamp=time.time(), adapter="x", coherence=0.90,
            productivity=None, tension=0.35, response_length=100,
            multi_perspective=False, user_continued=user_continued))

    def test_outcome_term_changes_the_score(self):
        landed = self._q(True)
        failed = self._q(False)
        unmeasured = self._q(None)
        self.assertGreater(landed, failed)
        # Abstention must sit between, not act as a silent penalty or bonus:
        # it renormalises the remaining weights rather than scoring anything.
        self.assertLess(failed, unmeasured)
        self.assertLessEqual(unmeasured, landed)

    def test_outcome_term_outweighs_adapter_noise(self):
        """The whole point: this must be big enough to break the tie.

        Measured on the real shadow log, adapters differ by ~0.013 in mean
        coherence against ~0.063 of within-adapter noise, so the winner of any
        window is decided by noise and every boost decays. A useful outcome
        term has to be substantially larger than that 0.013.
        """
        spread = self._q(True) - self._q(False)
        self.assertGreater(spread, 0.05, "outcome term too small to discriminate")


class TestFromSessionHistory(unittest.TestCase):
    """The wrapper the server actually calls, reading real session messages."""

    PREV = [
        {"role": "user", "content": "Why won't the optimizer go live?"},
        {"role": "assistant",
         "content": "Because user_continued is never measured, so the reward "
                    "has no outcome term and rests on coherence and tension "
                    "proxies alone.",
         "metadata": {"adapter": "newton"}},
    ]

    def test_reads_previous_exchange(self):
        r = classify_from_history(self.PREV, "How do we measure that outcome term?")
        self.assertIs(r.value, True)

    def test_correction_through_history(self):
        r = classify_from_history(self.PREV, "No, that's not the reason.")
        self.assertIs(r.value, False)

    def test_empty_history_abstains(self):
        self.assertIsNone(classify_from_history([], "first question").value)

    def test_malformed_history_never_raises(self):
        """A measurement problem must never break a turn."""
        for bad in ([{"nope": 1}], [None], "not a list", [{"role": "user"}]):
            with self.subTest(bad=bad):
                r = classify_from_history(bad, "some query")
                self.assertIsNone(r.value)


class TestAcknowledgementVariants(unittest.TestCase):
    """Stacked acknowledgements are how people actually close a turn."""

    PREV = ("Explain the decay term.",
            "Every boost fades 10% per step and must be re-earned.")

    def test_multi_word_acknowledgements_are_labelled_correctly(self):
        for ack in ("ok thanks", "yep got it, cheers", "Great, thanks!", "perfect"):
            with self.subTest(ack=ack):
                r = classify_engagement(*self.PREV, ack)
                self.assertIsNone(r.value)
                self.assertIn("acknowledgement", r.reason,
                              "verdict was right but the logged reason was not")

    def test_acknowledgement_prefix_with_real_content_is_not_an_ack(self):
        """'ok but...' carries a question; it must not be filed as a closing."""
        r = classify_engagement(*self.PREV, "ok but what about the reward term?")
        self.assertNotIn("acknowledgement", r.reason)


class TestThresholds(unittest.TestCase):
    def test_thresholds_are_sane(self):
        self.assertGreater(RE_ASK_THRESHOLD, 0.5)
        self.assertLess(RE_ASK_THRESHOLD, 1.0)
        self.assertGreater(UPTAKE_THRESHOLD, 0.0)
        self.assertLess(UPTAKE_THRESHOLD, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
