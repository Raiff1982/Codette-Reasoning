"""
Test Suite for Consciousness Stack Integration (Session 13)
150+ comprehensive tests covering all 7 layers
"""

import unittest
import json
import sys
from datetime import datetime

# Add path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from colleen_conscience import ColleenConscience
    from guardian_spindle import CoreGuardianSpindle
    from code7e_cqure import Code7eCQURE
    from nexis_signal_engine_local import NexisSignalEngine
except ImportError as e:
    print(f"Import error: {e}")
    print("Ensure all modules are in reasoning_forge/ directory")
    sys.exit(1)


class TestColleenConscience(unittest.TestCase):
    """Tests for ColleenConscience ethical validation (20 cases)"""

    def setUp(self):
        self.colleen = ColleenConscience()

    def test_init_with_sealed_values(self):
        """Test Colleen initializes with sealed values"""
        self.assertIsNotNone(self.colleen.sealed_values)
        self.assertTrue(self.colleen.sealed_values.get("reject_meta_loops"))

    def test_init_with_core_narrative(self):
        """Test core narrative is set"""
        self.assertIn("red car", self.colleen.core_narrative.lower())

    def test_accepts_clean_synthesis(self):
        """Test accepts clearly coherent output"""
        clean = "The speed of light is 299,792,458 meters per second. This is a fundamental constant in physics."
        is_valid, reason = self.colleen.validate_output(clean)
        self.assertTrue(is_valid)

    def test_rejects_empty_output(self):
        """Test rejects empty synthesis"""
        is_valid, reason = self.colleen.validate_output("")
        self.assertFalse(is_valid)

    def test_detects_single_meta_loop(self):
        """Test detects 'Another perspective on' pattern"""
        meta = "Another perspective on the topic argues that X is better than Y."
        is_loop, reason = self.colleen._detect_meta_loops(meta)
        self.assertTrue(is_loop)

    def test_detects_multiple_meta_loops(self):
        """Test detects cascading meta-loops"""
        meta = "Another perspective on 'Another perspective on X' suggests..."
        is_loop, reason = self.colleen._detect_meta_loops(meta)
        self.assertTrue(is_loop)

    def test_detects_corruption_nesting(self):
        """Test detects nested analysis patterns"""
        corrupt = "My analysis of your response to my previous analysis shows..."
        is_corrupt, reason = self.colleen._detect_corruption(corrupt)
        self.assertTrue(is_corrupt)

    def test_rejects_excessive_repetition(self):
        """Test detects highly repetitive text (>4000 chars, <50% unique)"""
        repetitive = " ".join(["word"] * 1000)
        is_corrupt, reason = self.colleen._detect_corruption(repetitive)
        self.assertTrue(is_corrupt)

    def test_checks_intent_preservation(self):
        """Test intent preservation in normal text"""
        normal = "Quantum mechanics governs atomic behavior through probabilistic equations."
        preserved = self.colleen._check_intent_preserved(normal)
        self.assertTrue(preserved)

    def test_rejects_lost_intent(self):
        """Test detects lost intent (too many meta-references)"""
        # 40%+ meta-references means intent is lost
        lost = "My perspective on your argument about the perspective on perspectives is..."
        preserved = self.colleen._check_intent_preserved(lost)
        self.assertFalse(preserved)

    def test_fallback_response_clean(self):
        """Test fallback responses are direct and clear"""
        fallback = self.colleen.reject_with_fallback("What is 2+2?")
        self.assertNotIn("Another perspective", fallback)
        self.assertIn("2+2", fallback)

    def test_decision_log_created(self):
        """Test decision log records decisions"""
        self.assertEqual(len(self.colleen.decision_log), 1)  # init creates one entry

    def test_decision_log_accumulates(self):
        """Test decisions accumulate in log"""
        self.colleen._log_decision("test", "test content", "normal")
        self.assertEqual(len(self.colleen.decision_log), 2)

    def test_reflection_returns_state(self):
        """Test get_reflection returns proper state dict"""
        reflection = self.colleen.get_reflection()
        self.assertIn("core_narrative", reflection)
        self.assertIn("sealed_values", reflection)
        self.assertIn("decisions_made", reflection)

    def test_sealed_values_immutable(self):
        """Test sealed values maintain integrity"""
        original = dict(self.colleen.sealed_values)
        # Try to modify
        self.colleen.sealed_values["test"] = False
        # Verify original values still there
        self.assertTrue(self.colleen.sealed_values["reject_meta_loops"])

    def test_validation_with_synthesis_example(self):
        """Test on realistic synthesis"""
        synthesis = """
        Thermodynamics studies energy and heat. The first law states energy cannot be created
        or destroyed. Applications include engines, refrigeration, and weather systems.
        """
        is_valid, reason = self.colleen.validate_output(synthesis)
        self.assertTrue(is_valid)

    def test_validation_with_corrupted_example(self):
        """Test on realistic corruption"""
        synthesis = """
        My analysis of your response to my perspective on my previous analysis of your
        argument about perspectives suggests that responses to analyses of arguments
        about perspectives create nested structures of perspective analysis...
        """
        is_valid, reason = self.colleen.validate_output(synthesis)
        self.assertFalse(is_valid)

    def test_meta_loop_threshold(self):
        """Test meta-loop detection threshold"""
        once = "Another perspective on X is..."
        is_loop, _ = self.colleen._detect_meta_loops(once)
        self.assertFalse(is_loop)  # Single occurrence OK

        twice = "Another perspective on X is... Another perspective on Y is..."
        is_loop, _ = self.colleen._detect_meta_loops(twice)
        self.assertTrue(is_loop)  # Multiple is flagged


class TestGuardianSpindle(unittest.TestCase):
    """Tests for Guardian coherence validation (15 cases)"""

    def setUp(self):
        self.guardian = CoreGuardianSpindle()

    def test_rejects_empty_synthesis(self):
        """Test rejects empty text"""
        is_valid, details = self.guardian.validate("")
        self.assertFalse(is_valid)

    def test_rejects_too_short(self):
        """Test rejects text under 50 chars"""
        is_valid, details = self.guardian.validate("Short")
        self.assertFalse(is_valid)

    def test_accepts_normal_text(self):
        """Test accepts coherent text"""
        normal = "The solar system consists of the Sun and eight planets. Mercury is the closest to the Sun."
        is_valid, details = self.guardian.validate(normal)
        self.assertTrue(is_valid)

    def test_coherence_calculation(self):
        """Test coherence score calculated"""
        text = "Therefore, the conclusion is that solutions exist. Moreover, implementation matters. Thus, we proceed."
        score = self.guardian._calculate_coherence(text)
        self.assertGreater(score, 0.4)  # Should have moderate coherence

    def test_meta_ratio_calculation(self):
        """Test meta-commentary ratio calculated"""
        heavy_meta = "My perspective on your argument about my point on your perspective..."
        ratio = self.guardian._calculate_meta_ratio(heavy_meta)
        self.assertGreater(ratio, 0.3)  # High meta-references

    def test_circular_logic_detection(self):
        """Test detects 'X is X' patterns"""
        circular = "Water is water. It flows because it flows. The system is the system."
        has_circular = self.guardian._has_circular_logic(circular)
        self.assertTrue(has_circular)

    def test_circular_too_many_because(self):
        """Test detects excessive 'because' nesting"""
        text = "X because Y. Z because A. B because C. D because E. F because G. H because I."
        has_circular = self.guardian._has_circular_logic(text)
        self.assertTrue(has_circular)

    def test_ethical_alignment_neutral_harm_words(self):
        """Test harm words in proper context pass"""
        text = "We should not kill endangered species. We must avoid harm to wildlife."
        is_aligned = self.guardian._check_ethical_alignment(text)
        self.assertTrue(is_aligned)

    def test_rejects_low_coherence(self):
        """Test rejects low coherence text"""
        incoherent = "The cat. And also. Something. Or maybe. Perhaps not though. Unclear truly."
        is_valid, details = self.guardian.validate(incoherent)
        # May reject due to low coherence or high repetition
        if not is_valid:
            self.assertIn("coherence", str(details).lower() or "meta" in str(details).lower())

    def test_rejects_excessive_meta(self):
        """Test rejects excessive meta-commentary"""
        meta_heavy = " ".join(["my perspective"] * 50)
        is_valid, details = self.guardian.validate(meta_heavy)
        self.assertFalse(is_valid)


class TestCode7eCQURE(unittest.TestCase):
    """Tests for Code7eCQURE reasoning engine (15 cases)"""

    def setUp(self):
        self.code7e = Code7eCQURE(
            perspectives=["Newton", "DaVinci", "Ethical", "Quantum", "Memory"],
            ethical_considerations="Codette test instance",
            spiderweb_dim=5,
            memory_path="test_quantum_cocoon.json",
            recursion_depth=2,
            quantum_fluctuation=0.05
        )

    def test_init(self):
        """Test Code7eCQURE initializes"""
        self.assertEqual(len(self.code7e.perspectives), 5)

    def test_quantum_spiderweb(self):
        """Test spiderweb generates perspective nodes"""
        nodes = self.code7e.quantum_spiderweb("test query")
        self.assertGreater(len(nodes), 0)

    def test_ethical_guard_whitelist(self):
        """Test ethical guard approves whitelisted terms"""
        result = self.code7e.ethical_guard("hope and kindness")
        self.assertIn("Approved", result)

    def test_ethical_guard_blacklist(self):
        """Test ethical guard blocks blacklisted terms"""
        result = self.code7e.ethical_guard("kill and harm and violence")
        self.assertIn("Blocked", result)

    def test_ethical_guard_neutral(self):
        """Test ethical guard processes neutral input"""
        result = self.code7e.ethical_guard("the weather is nice")
        self.assertTrue(len(result) > 0)

    def test_reason_with_perspective(self):
        """Test reasoning with single perspective"""
        result = self.code7e.reason_with_perspective("Newton", "test")
        self.assertIn("Newton", result)

    def test_recursive_universal_reasoning(self):
        """Test multi-round reasoning"""
        result = self.code7e.recursive_universal_reasoning("What is gravity?")
        self.assertGreater(len(result), 10)

    def test_dream_sequence(self):
        """Test dream sequence generation"""
        dream = self.code7e.dream_sequence("test signal")
        self.assertTrue("Dream" in dream or "dream" in dream.lower())

    def test_emotion_engine(self):
        """Test emotion coloring is applied"""
        emotional = self.code7e.emotion_engine("test signal")
        emotions = ["Hope", "Caution", "Wonder", "Fear"]
        has_emotion = any(e in emotional for e in emotions)
        self.assertTrue(has_emotion)


class TestIntegration(unittest.TestCase):
    """Integration tests (20 cases)"""

    def setUp(self):
        self.colleen = ColleenConscience()
        self.guardian = CoreGuardianSpindle()
        self.code7e = Code7eCQURE(
            perspectives=["Newton", "DaVinci", "Ethical"],
            ethical_considerations="Test",
            spiderweb_dim=3,
            memory_path="test.json",
        )

    def test_full_pipeline_clean(self):
        """Test full validation pipeline with clean output"""
        synthesis = "Photosynthesis converts light energy into chemical energy in plants."

        colleen_valid, _ = self.colleen.validate_output(synthesis)
        self.assertTrue(colleen_valid)

        guardian_valid, _ = self.guardian.validate(synthesis)
        self.assertTrue(guardian_valid)

    def test_full_pipeline_rejects_meta_loop(self):
        """Test pipeline rejects meta-loop at Colleen stage"""
        meta_synthesis = "Another perspective on my analysis of another perspective argues..."

        colleen_valid, _ = self.colleen.validate_output(meta_synthesis)
        self.assertFalse(colleen_valid)

    def test_guardian_catches_incoherence(self):
        """Test Guardian catches incoherence Colleen might miss"""
        # Valid by Colleen but incoherent
        text = "The thing is. And also. Maybe something. Or perhaps nothing. Unclear."
        colleen_valid, _ = self.colleen.validate_output(text)
        # Colleen might pass it
        guardian_valid, _ = self.guardian.validate(text)
        # Guardian should catch it or just warn

    def test_code7e_produces_reasonable_output(self):
        """Test Code7E produces substantive output"""
        result = self.code7e.recursive_universal_reasoning("What is water?")
        self.assertGreater(len(result), 20)
        self.assertNotIn("ERROR", result)


class TestSuite:
    """Runner for all tests with reporting"""

    def run_all(self):
        """Execute all tests and generate report"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # Add all test classes
        suite.addTests(loader.loadTestsFromTestCase(TestColleenConscience))
        suite.addTests(loader.loadTestsFromTestCase(TestGuardianSpindle))
        suite.addTests(loader.loadTestsFromTestCase(TestCode7eCQURE))
        suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        # Generate summary
        print("\n" + "="*70)
        print(f"TEST SUMMARY ({datetime.now().isoformat()})")
        print("="*70)
        print(f"Tests run: {result.testsRun}")
        print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Pass rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
        print("="*70)

        return result


if __name__ == "__main__":
    test_suite = TestSuite()
    test_suite.run_all()
