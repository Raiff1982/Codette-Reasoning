#!/usr/bin/env python3
"""Codette Self-Correction Engine — Autonomous constraint compliance

Three systems working together:

1. SELF-CORRECTION LOOP (check_violations → re-prompt if needed)
   Detects constraint violations BEFORE sending the response.
   If the model's output violates constraints, it re-generates with
   explicit correction instructions. Max 1 retry to avoid latency.

2. PERSISTENT BEHAVIOR MEMORY (learn from mistakes)
   Stores constraint violation/success patterns as cocoon memories.
   On startup, loads past lessons and injects them into the system prompt
   so the model learns from its own history across sessions.

3. CHAOS DETECTOR (graceful degradation under competing pressures)
   When multiple constraints + uncertainty + mode personality collide,
   detects the "chaos level" and applies a simplify-first strategy
   instead of letting the model collapse into incoherence.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ================================================================
# 1. SELF-CORRECTION: Violation detection
# ================================================================

def detect_violations(response: str, constraints: dict) -> List[str]:
    """Check a response against constraints and return list of violations.

    Returns empty list if response is compliant.
    """
    violations = []

    if not response or not constraints:
        return violations

    words = response.split()
    word_count = len(words)

    # Check word limit
    max_words = constraints.get('max_words')
    if max_words and word_count > max_words:
        violations.append(f"WORD_LIMIT: {word_count} words exceeds limit of {max_words}")

    # Check sentence limit
    max_sentences = constraints.get('max_sentences')
    if max_sentences:
        sentences = re.split(r'(?<=[.!?])\s+', response.strip())
        # Filter out empty strings
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) > max_sentences:
            violations.append(f"SENTENCE_LIMIT: {len(sentences)} sentences exceeds limit of {max_sentences}")

    # Check incomplete sentence (ends with dangling word or no punctuation)
    if response and response[-1] not in '.!?':
        violations.append("INCOMPLETE: Response does not end with proper punctuation")

    # Check dangling words at end
    _DANGLING = {
        'that', 'which', 'who', 'with', 'and', 'but', 'or', 'the', 'a', 'an',
        'in', 'on', 'of', 'for', 'to', 'by', 'from', 'as', 'if', 'because',
        'including', 'is', 'are', 'was', 'were', 'has', 'have', 'had',
    }
    if words:
        last_word = words[-1].lower().rstrip('.,;:!?')
        if last_word in _DANGLING and response[-1] == '.':
            # Ends with a dangling word + forced period = likely truncated
            violations.append(f"DANGLING: Response ends with '{words[-1]}' (likely truncated)")

    # Check binary constraint
    if constraints.get('binary'):
        first_word = words[0].lower().rstrip('.,;:!?') if words else ''
        if first_word not in ('yes', 'no', 'true', 'false'):
            violations.append("BINARY: Response should start with Yes/No")

    # Check brevity — soft check, flag if over 30 words
    if constraints.get('brevity') and word_count > 30:
        violations.append(f"BREVITY: {word_count} words is not brief (target: under 30)")

    return violations


def universal_self_check(response: str) -> Tuple[str, List[str]]:
    """PERMANENT LOCK enforcement — runs on EVERY response, not just constrained ones.

    Enforces Lock 1 (Answer→Stop), Lock 3 (self-check), Lock 4 (no incomplete outputs).
    Returns (cleaned_response, issues_found).
    """
    issues = []
    if not response:
        return response, issues

    cleaned = response.rstrip()

    # LOCK 3: Self-check — detect echo-back failures (model repeating the question)
    echo_patterns = [
        r'^You (?:received|asked|said|mentioned|wrote)(?:\s+this)?\s*(?:question|query)?[:\s]',
        r'^The (?:question|query) (?:is|was)[:\s]',
        r'^(?:Your|The) question[:\s]',
        r'^(?:Here is|I received|Let me|I will)\s+(?:the|your|this)\s+(?:question|query)',
    ]
    is_echo = False
    for ep in echo_patterns:
        if re.match(ep, cleaned, re.I):
            is_echo = True
            # Strip the echo line and return whatever follows
            lines = cleaned.split('\n')
            non_echo = [l for l in lines if not re.match(ep, l.strip(), re.I)]
            # Also strip lines that are just the quoted question
            non_echo = [l for l in non_echo if l.strip() and not l.strip().startswith('"')]
            if non_echo:
                cleaned = '\n'.join(non_echo).strip()
                issues.append("LOCK3_FIX: Removed question echo-back")
            else:
                # Nothing left after echo removal — model completely failed
                # Return empty so the caller knows to use fallback
                cleaned = ""
                issues.append("LOCK3_FAIL: Model echoed question without answering")
            break

    # LOCK 4: No incomplete outputs — fix missing punctuation
    if cleaned and cleaned[-1] not in '.!?"\')\u2019':
        words = cleaned.split()
        _DANGLING = {
            'that', 'which', 'who', 'with', 'and', 'but', 'or', 'the', 'a', 'an',
            'in', 'on', 'of', 'for', 'to', 'by', 'from', 'as', 'if', 'because',
            'including', 'is', 'are', 'was', 'were', 'has', 'have', 'had',
            'not', 'very', 'also', 'just', 'even', 'still', 'such', 'like',
        }
        # Strip dangling words from end
        while len(words) > 1 and words[-1].lower().rstrip('.,;:!?') in _DANGLING:
            words.pop()
            issues.append("LOCK4_FIX: Removed dangling word from end")
        cleaned = ' '.join(words)
        cleaned = cleaned.rstrip(' ,;:—-')
        if cleaned and cleaned[-1] not in '.!?"\')\u2019':
            cleaned += '.'
            issues.append("LOCK4_FIX: Added missing end punctuation")

    # LOCK 1: Answer→Stop — detect and trim post-answer drift
    sentences = re.split(r'(?<=[.!?])\s+', cleaned.strip())
    sentences = [s for s in sentences if s.strip()]

    if len(sentences) > 2:
        # Check for drift indicators in later sentences (from 2nd sentence onward)
        drift_phrases = [
            r"^(?:furthermore|moreover|additionally|in addition|it(?:'|\u2019)s worth noting)",
            r'^(?:this (?:is|means|suggests|implies|shows|demonstrates|highlights|reveals))',
            r'^(?:one (?:could|might|may) (?:argue|say|suggest))',
            r'^(?:from (?:a|an|the) \w+ perspective)',
            r'^(?:in (?:other words|essence|summary|fact))',
            r'^(?:by (?:acknowledging|understanding|exploring|examining|considering))',
            r'^(?:understanding \w+ requires)',
            r'^(?:it is (?:important|worth|essential|notable|key) to (?:note|understand|recognize|remember))',
        ]
        drift_pattern = re.compile('|'.join(drift_phrases), re.I)

        cut_at = None
        for i in range(2, len(sentences)):  # Check from 3rd sentence onward
            if drift_pattern.match(sentences[i]):
                cut_at = i
                break

        if cut_at is not None:
            cleaned = ' '.join(sentences[:cut_at])
            if cleaned and cleaned[-1] not in '.!?':
                cleaned += '.'
            issues.append(f"LOCK1_TRIM: Removed {len(sentences) - cut_at} drift sentence(s)")

    # LOCK 1 softcap: Unconstrained responses shouldn't over-talk
    # If more than 60 words with no explicit constraints, trim to last complete
    # sentence within ~60 words. This enforces "Answer → Stop" as DEFAULT behavior.
    words = cleaned.split()
    if len(words) > 60:
        sentences = re.split(r'(?<=[.!?])\s+', cleaned.strip())
        sentences = [s for s in sentences if s.strip()]
        fitted = []
        wc = 0
        for s in sentences:
            sw = len(s.split())
            if wc + sw <= 60:
                fitted.append(s)
                wc += sw
            else:
                # Allow one more sentence if we're close and it's short
                if wc >= 30 and sw <= 15:
                    fitted.append(s)
                break
        if fitted and len(fitted) < len(sentences):
            cleaned = ' '.join(fitted)
            if cleaned and cleaned[-1] not in '.!?':
                cleaned += '.'
            issues.append(f"LOCK1_SOFTCAP: Trimmed from {len(words)} to {len(cleaned.split())} words")

    # LOCK 4 final check: Ensure the final output is complete
    if cleaned and cleaned[-1] not in '.!?"\')\u2019':
        cleaned += '.'
        issues.append("LOCK4_FIX: Final punctuation check")

    return cleaned, issues


def build_correction_prompt(original_response: str, violations: List[str],
                            constraints: dict, query: str) -> str:
    """Build a correction prompt that tells the model exactly what it did wrong.

    This is sent as a follow-up user message to get a corrected response.
    """
    violation_text = "\n".join(f"  - {v}" for v in violations)

    constraint_text = []
    if 'max_words' in constraints:
        constraint_text.append(f"maximum {constraints['max_words']} words")
    if 'max_sentences' in constraints:
        constraint_text.append(f"maximum {constraints['max_sentences']} sentence(s)")
    if constraints.get('brevity'):
        constraint_text.append("be brief")
    if constraints.get('binary'):
        constraint_text.append("answer Yes or No")

    return (
        f"Your previous answer violated these constraints:\n{violation_text}\n\n"
        f"The required constraints are: {', '.join(constraint_text)}.\n\n"
        f"Rewrite your answer to the original question: \"{query}\"\n"
        f"This time, STRICTLY obey the constraints. "
        f"If you can't fit everything, SIMPLIFY — say the right thing cleanly. "
        f"Do NOT end mid-sentence. Give a COMPLETE thought within the limits."
    )


# ================================================================
# 2. PERSISTENT BEHAVIOR MEMORY
# ================================================================

_BEHAVIOR_MEMORY_FILE = "cocoons/behavior_memory.json"


class BehaviorMemory:
    """Persistent memory of constraint successes and failures.

    Stores patterns like:
    - "When asked for 'one sentence under 10 words' with philosophy mode,
       I over-explained. The correct approach: simplify to core answer."
    - "When asked 'yes or no', I answered directly. Keep doing this."

    These are loaded on startup and injected into the system prompt
    as learned behaviors.
    """

    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or _BEHAVIOR_MEMORY_FILE)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lessons: List[Dict] = []
        self._max_lessons = 50  # Rolling window
        self._load()

    def _load(self):
        """Load lessons from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                self.lessons = data.get("lessons", [])[-self._max_lessons:]
            except Exception:
                self.lessons = []

    def _save(self):
        """Save lessons to disk."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump({
                    "lessons": self.lessons[-self._max_lessons:],
                    "updated_at": time.time(),
                }, f, indent=2)
        except Exception as e:
            print(f"  [BEHAVIOR] Save failed: {e}")

    def record_violation(self, query: str, constraints: dict, violations: List[str],
                         adapter: str, response_preview: str):
        """Record a constraint violation for future learning."""
        lesson = {
            "type": "violation",
            "timestamp": time.time(),
            "adapter": adapter,
            "constraints": constraints,
            "violations": violations,
            "query_preview": query[:80],
            "response_preview": response_preview[:100],
            "lesson": self._derive_lesson(constraints, violations, adapter),
        }
        self.lessons.append(lesson)
        self._save()

    def record_success(self, query: str, constraints: dict, adapter: str,
                       word_count: int):
        """Record a successful constraint compliance."""
        lesson = {
            "type": "success",
            "timestamp": time.time(),
            "adapter": adapter,
            "constraints": constraints,
            "word_count": word_count,
            "query_preview": query[:80],
        }
        self.lessons.append(lesson)
        self._save()

    def _derive_lesson(self, constraints: dict, violations: List[str],
                       adapter: str) -> str:
        """Derive a human-readable lesson from a violation."""
        parts = []

        for v in violations:
            if "WORD_LIMIT" in v:
                parts.append(f"With {adapter} mode, I exceeded the word limit. I must count words and simplify.")
            elif "SENTENCE_LIMIT" in v:
                parts.append(f"With {adapter} mode, I used too many sentences. One complete thought is enough.")
            elif "INCOMPLETE" in v:
                parts.append("I ended a sentence incomplete. I must finish thoughts cleanly or simplify.")
            elif "DANGLING" in v:
                parts.append("I ended with a connecting word (cut-off). I must close the thought before the limit.")
            elif "BINARY" in v:
                parts.append("I didn't start with Yes/No when asked for a binary answer.")
            elif "BREVITY" in v:
                parts.append(f"With {adapter} mode, I over-explained when asked to be brief.")

        return " ".join(parts) if parts else "Constraint violation occurred."

    def get_lessons_for_prompt(self, max_lessons: int = 5) -> str:
        """Build a system prompt section from recent lessons.

        Returns a string to inject into the system prompt that teaches
        the model from its own past mistakes.
        """
        # Get recent violations (most valuable for learning)
        violations = [l for l in self.lessons if l["type"] == "violation"]
        if not violations:
            return ""

        # Take the most recent unique lessons
        seen_lessons = set()
        unique_lessons = []
        for v in reversed(violations):
            lesson = v.get("lesson", "")
            if lesson and lesson not in seen_lessons:
                seen_lessons.add(lesson)
                unique_lessons.append(lesson)
                if len(unique_lessons) >= max_lessons:
                    break

        if not unique_lessons:
            return ""

        lines = "\n".join(f"  - {l}" for l in unique_lessons)
        return (
            f"\n\nLEARNED FROM PAST MISTAKES (apply these lessons):\n{lines}\n"
            "Remember: constraints always override modes. Simplify rather than truncate."
        )

    def get_stats(self) -> Dict:
        """Get behavior memory statistics."""
        violations = [l for l in self.lessons if l["type"] == "violation"]
        successes = [l for l in self.lessons if l["type"] == "success"]
        return {
            "total_lessons": len(self.lessons),
            "violations": len(violations),
            "successes": len(successes),
            "compliance_rate": len(successes) / max(len(self.lessons), 1),
        }


# ================================================================
# 3. CHAOS DETECTION — graceful degradation under pressure
# ================================================================

def detect_chaos_level(query: str, constraints: dict, adapter: str) -> Tuple[int, List[str]]:
    """Detect how many competing pressures are active.

    Returns:
        (chaos_level: 0-5, pressure_list: list of active pressures)

    Chaos levels:
        0: No constraints, simple query → normal generation
        1: One constraint → straightforward compliance
        2: Two constraints → manageable, minor tension
        3: Three+ constraints → high tension, simplify-first strategy
        4: Constraints + uncertainty requirement + complex topic → danger zone
        5: All of above + mode conflict (philosophy on a binary question) → maximum simplification
    """
    pressures = []

    # Count hard constraints
    if constraints.get('max_words'):
        pressures.append(f"word_limit={constraints['max_words']}")
    if constraints.get('max_sentences'):
        pressures.append(f"sentence_limit={constraints['max_sentences']}")
    if constraints.get('brevity'):
        pressures.append("brevity")
    if constraints.get('binary'):
        pressures.append("binary_answer")
    if constraints.get('list_format'):
        pressures.append("list_format")

    # Check for uncertainty requirement
    uncertainty_words = ['uncertain', 'uncertainty', 'maybe', 'might', 'possibly',
                         'include uncertainty', 'not sure', 'debatable']
    query_lower = query.lower()
    if any(w in query_lower for w in uncertainty_words):
        pressures.append("uncertainty_required")

    # Check for complex topic (would normally trigger verbose mode)
    complex_topics = ['consciousness', 'free will', 'meaning of life', 'quantum',
                      'philosophy', 'ethics', 'morality', 'existence', 'reality',
                      'epistemology', 'ontology', 'metaphysics']
    if any(t in query_lower for t in complex_topics):
        pressures.append("complex_topic")

    # Check for mode conflict (verbose mode + tight constraint)
    verbose_modes = {'philosophy', 'consciousness', 'multi_perspective', 'quantum'}
    tight_constraints = bool(constraints.get('max_words') or constraints.get('max_sentences')
                             or constraints.get('binary') or constraints.get('brevity'))
    if adapter in verbose_modes and tight_constraints:
        pressures.append(f"mode_conflict:{adapter}")

    chaos_level = min(len(pressures), 5)
    return chaos_level, pressures


def build_chaos_mitigation(chaos_level: int, pressures: List[str]) -> str:
    """Build additional system prompt guidance for high-chaos situations.

    At chaos level 3+, we inject explicit simplification strategies.
    """
    if chaos_level < 3:
        return ""

    if chaos_level == 3:
        return (
            "\n\nMULTIPLE COMPETING PRESSURES DETECTED. Strategy: "
            "SIMPLIFY FIRST. Give the simplest correct answer that satisfies "
            "ALL constraints. Do not try to be comprehensive — be precise. "
            "One clean thought is better than a cramped paragraph.\n"
        )
    elif chaos_level == 4:
        return (
            "\n\nHIGH CONSTRAINT PRESSURE DETECTED. Strategy: "
            "CORE ANSWER ONLY. Strip everything to the essential truth. "
            "No qualifiers, no hedging, no mode-specific elaboration. "
            "If the topic is complex but the constraint is tight, "
            "give the most important single insight cleanly.\n"
        )
    else:  # chaos_level >= 5
        return (
            "\n\nMAXIMUM CONSTRAINT PRESSURE. Strategy: "
            "OVERRIDE ALL MODES. Your personality mode is SUSPENDED for this response. "
            "You are a plain, direct answerer. Give the shortest correct answer "
            "that satisfies every constraint. No philosophy, no creativity, no "
            "exploration — just the answer. If asked yes/no, say yes or no. "
            "If given a word limit, count your words. Nothing else matters.\n"
        )
