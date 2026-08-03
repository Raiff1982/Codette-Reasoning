#!/usr/bin/env python3
"""Perspectives must have distinct goals, honest limits, and a named successor.

This exists because of a measurement, not a preference. Across 167 shadow turns
the adapters differ by ~0.013 in mean coherence against ~0.063 of within-adapter
noise, so the optimizer's "best adapter" in any window is decided by noise and
every boost decays to zero. A full 8-perspective synthesis returned eight
paraphrases of one answer.

The cause was that every system prompt was the same template with different
adjectives: "You are Codette, reasoning with X. Approach problems through
A, B, C, D." A style is not a goal, and identical instruction shapes produce
identical answer shapes.

So these tests assert the property that has to hold for multi-perspective
reasoning to mean anything: the perspectives must be genuinely different, must
say when they are the wrong tool, and must name who to hand to.
"""
import unittest

from reasoning_forge.perspective_registry import PERSPECTIVES


class TestEveryPerspectiveIsSpecified(unittest.TestCase):

    def test_all_have_a_goal(self):
        for name, p in PERSPECTIVES.items():
            with self.subTest(perspective=name):
                self.assertTrue(p.goal.strip(), f"{name} has no goal")

    def test_all_state_what_the_answer_must_contain(self):
        for name, p in PERSPECTIVES.items():
            with self.subTest(perspective=name):
                self.assertGreaterEqual(
                    len(p.answer_must), 2,
                    f"{name} needs concrete obligations, not just a mood")

    def test_all_admit_what_they_are_bad_at(self):
        """The honest half. A perspective that claims no weakness is not
        specified, it is just confident."""
        for name, p in PERSPECTIVES.items():
            with self.subTest(perspective=name):
                self.assertTrue(p.not_for.strip(), f"{name} claims no limits")

    def test_all_name_a_successor(self):
        """'Best choice' has to be expressible, not implied."""
        for name, p in PERSPECTIVES.items():
            with self.subTest(perspective=name):
                self.assertTrue(p.defers_to, f"{name} defers to nobody")
                for target in p.defers_to:
                    self.assertIn(target, PERSPECTIVES,
                                  f"{name} defers to unknown '{target}'")
                self.assertNotIn(name, p.defers_to,
                                 f"{name} defers to itself")

    def test_is_specified_property_agrees(self):
        for name, p in PERSPECTIVES.items():
            with self.subTest(perspective=name):
                self.assertTrue(p.is_specified)


class TestGoalsAreActuallyDistinct(unittest.TestCase):
    """The whole point. If two perspectives want the same thing, they are one
    perspective with two names, and no router can meaningfully choose."""

    @staticmethod
    def _words(text):
        stop = {"the", "and", "a", "an", "of", "to", "in", "is", "it", "that",
                "what", "not", "for", "on", "or", "be", "this", "with", "at",
                "by", "as", "from", "than", "then", "into", "its", "their",
                "which", "who", "how", "why", "where", "when", "are", "was"}
        return {w.strip(".,—-—:;()'\"").lower()
                for w in text.split()
                if len(w) > 3 and w.lower() not in stop}

    def test_no_two_goals_are_near_duplicates(self):
        names = list(PERSPECTIVES)
        worst = (0.0, "", "")
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                wa = self._words(PERSPECTIVES[a].goal)
                wb = self._words(PERSPECTIVES[b].goal)
                if not wa or not wb:
                    continue
                overlap = len(wa & wb) / len(wa | wb)
                if overlap > worst[0]:
                    worst = (overlap, a, b)
                self.assertLess(
                    overlap, 0.5,
                    f"goals of '{a}' and '{b}' overlap {overlap:.2f} — "
                    f"these are the same perspective twice")
        # Informational: surfaces the closest pair when this file is run direct.
        if __name__ == "__main__":
            print(f"\nclosest goal pair: {worst[1]}/{worst[2]} = {worst[0]:.2f}")

    def test_obligations_are_not_shared_boilerplate(self):
        """If every perspective's obligations were identical, the outputs would
        converge again by a different route."""
        all_obligations = [tuple(sorted(p.answer_must))
                           for p in PERSPECTIVES.values()]
        self.assertEqual(len(set(all_obligations)), len(all_obligations),
                         "two perspectives share an identical obligation set")


class TestBuiltPrompt(unittest.TestCase):

    def test_prompt_carries_goal_obligations_and_limits(self):
        p = PERSPECTIVES["newton"]
        prompt = p.build_system_prompt()
        self.assertIn("YOUR GOAL", prompt)
        self.assertIn("YOUR ANSWER MUST", prompt)
        self.assertIn("WRONG PERSPECTIVE FOR", prompt)
        for obligation in p.answer_must:
            self.assertIn(obligation, prompt)

    def test_prompt_permits_handing_over(self):
        """Deferring must read as an OPTION, not an obligation.

        Reworded 2026-08-03 after asking Codette directly how the earlier
        phrasing landed. It said "handing over is a correct answer, not a
        failure", which sounds permissive; she read it, at confidence 1.0, as
        "a directive rather than permission... my primary responsibility is to
        recognize the limitations of my abilities."

        A clause written to free her to decline was landing as a standing duty
        to find herself wanting — the same shape as choosing the more
        restrictive rule about her own conscience at zero confidence and then
        calling it an attempt to appear cautious. So the test now asserts the
        properties that actually matter: answering anyway is explicitly
        allowed, and neither choice is penalised.
        """
        prompt = PERSPECTIVES["empathy"].build_system_prompt()
        self.assertIn("you may simply say so", prompt)
        self.assertIn("free to answer anyway", prompt)
        self.assertIn("Neither choice counts against you", prompt)
        for target in PERSPECTIVES["empathy"].defers_to:
            self.assertIn(target, prompt)

    def test_deferral_clause_does_not_dwell_on_inadequacy(self):
        """The emphasis must sit on 'someone else is better placed', not on
        'you are limited'. Phrasing is the whole mechanism here."""
        for name, p in PERSPECTIVES.items():
            with self.subTest(perspective=name):
                prompt = p.build_system_prompt()
                for phrase in ("outside your competence",
                               "your limitations",
                               "not a failure"):
                    self.assertNotIn(phrase, prompt,
                                     f"{name}: '{phrase}' frames declining as a shortfall")

    def test_built_prompts_differ_from_each_other(self):
        prompts = {n: p.build_system_prompt() for n, p in PERSPECTIVES.items()}
        self.assertEqual(len(set(prompts.values())), len(prompts))

    def test_unspecified_perspective_falls_back_cleanly(self):
        from reasoning_forge.perspective_registry import Perspective
        bare = Perspective(name="x", display_name="X", adapter=None,
                           system_prompt="base prompt", keywords=[])
        self.assertFalse(bare.is_specified)
        self.assertEqual(bare.build_system_prompt(), "base prompt")


class TestDeferralGraph(unittest.TestCase):

    def test_deferral_is_not_universally_mutual(self):
        """A and B both deferring to each other on everything would be a loop
        with no exit. Some mutual pairs are legitimate (they are strong in
        opposite directions); a graph where EVERY edge is mutual is not."""
        mutual = sum(
            1 for n, p in PERSPECTIVES.items()
            for t in p.defers_to
            if n in PERSPECTIVES[t].defers_to
        )
        total = sum(len(p.defers_to) for p in PERSPECTIVES.values())
        self.assertLess(mutual / total, 0.75,
                        "deferral graph is almost entirely mutual — no exits")

    def test_every_perspective_is_the_best_choice_for_something(self):
        """Nobody may be a dead end.

        The first version of this graph failed here, and the failure was the
        useful part: seven of twelve were never deferred TO — davinci, quantum,
        consciousness, multi_perspective, human_intuition, resilient_kindness,
        bias_mitigation. Everything handed *up* to newton, mathematical and
        systems_architecture, which encodes a claim nobody would defend out
        loud: that creativity, intuition and fairness auditing are never the
        right answer, only fallbacks on the way to rigour.

        Each name already says when it wins. You go to Da Vinci exactly when
        the analysis is sound and the answer is "none of these options work" —
        that is not a fallback, it is the only perspective that can supply a
        new option. So the assertion is absolute: if nothing ever defers to a
        perspective, it is not a specialist, it is unreachable.
        """
        targets = {t for p in PERSPECTIVES.values() for t in p.defers_to}
        never = sorted(set(PERSPECTIVES) - targets)
        self.assertEqual(
            never, [],
            f"these are never anyone's best choice, so they are dead ends: {never}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
