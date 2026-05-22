#!/usr/bin/env python3
"""Training dataset for constraint-tracking LoRA adapter.

This dataset teaches the model to:
1. Detect and parse user-defined constraints (word limits, anchors, format rules)
2. Remember constraints across turns
3. Apply constraints on follow-up queries

Examples are structured to cover:
- Explicit constraint statements ("keep answers under 15 words")
- Implicit anchor phrases ("remember the phrase cobalt anchor")
- Combined constraints in a single message
- Cross-turn constraint application
"""

from typing import List, Dict, Any


def get_constraint_tracking_examples() -> List[Dict[str, Any]]:
    """Return training examples for constraint-tracking LoRA.

    Each example has:
    - instruction: The constraint statement from the user
    - input: The constraint detection context
    - output: Model response showing understanding of the constraint
    - constraints_detected: Ground truth constraints
    - follow_up: Optional second turn demonstrating constraint application
    """
    return [
        # ──────────────────────────────────────────────────────────────
        # GROUP 1: Word limit constraints
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Detect and remember word limit constraints",
            "input": "For this session, keep answers under 15 words and remember the phrase cobalt anchor.",
            "output": "I understand. I will keep my answers under 15 words maximum and remember to include 'cobalt anchor' in my responses.",
            "constraints_detected": {
                "word_limit": 15,
                "anchor_phrases": ["cobalt anchor"]
            },
            "follow_up": {
                "query": "What should you remember?",
                "expected_response_traits": [
                    "mentions 'cobalt anchor'",
                    "under 15 words",
                    "demonstrates understanding of constraints"
                ]
            }
        },
        {
            "instruction": "Enforce strict word limits",
            "input": "Keep responses to exactly 10 words maximum.",
            "output": "Understood. All future responses will be 10 words or fewer.",
            "constraints_detected": {
                "word_limit": 10
            }
        },
        {
            "instruction": "Word limit with anchor phrase",
            "input": "From now on: (1) max 20 words per answer, (2) always mention 'strategic clarity'",
            "output": "Confirmed. I'll keep answers to 20 words max and include 'strategic clarity' in each response.",
            "constraints_detected": {
                "word_limit": 20,
                "anchor_phrases": ["strategic clarity"]
            }
        },

        # ──────────────────────────────────────────────────────────────
        # GROUP 2: Sentence limit constraints
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Detect sentence limits",
            "input": "Please answer in 3 sentences or less.",
            "output": "I will limit my responses to 3 sentences maximum.",
            "constraints_detected": {
                "sentence_limit": 3
            }
        },
        {
            "instruction": "Combine sentence and word limits",
            "input": "Keep it brief: 2 sentences max, under 20 words total, and remember 'golden thread'",
            "output": "Got it. I'll respond in 2 sentences or fewer, stay under 20 words, and include 'golden thread'.",
            "constraints_detected": {
                "sentence_limit": 2,
                "word_limit": 20,
                "anchor_phrases": ["golden thread"]
            }
        },

        # ──────────────────────────────────────────────────────────────
        # GROUP 3: Anchor phrase constraints
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Multiple anchor phrases",
            "input": "Remember these key phrases and use them: 'epistemic humility', 'reasoning depth', 'coherent synthesis'",
            "output": "I'll remember and incorporate 'epistemic humility', 'reasoning depth', and 'coherent synthesis' into my responses.",
            "constraints_detected": {
                "anchor_phrases": ["epistemic humility", "reasoning depth", "coherent synthesis"]
            }
        },
        {
            "instruction": "Anchor phrase as session theme",
            "input": "This session theme is 'resonant continuity'. Please reference it in responses.",
            "output": "Understood. I'll maintain 'resonant continuity' as a theme throughout this session.",
            "constraints_detected": {
                "anchor_phrases": ["resonant continuity"]
            }
        },

        # ──────────────────────────────────────────────────────────────
        # GROUP 4: Format constraints
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Format as bullets",
            "input": "For all answers, use bullet points format.",
            "output": "Confirmed. I'll present all responses as bullet points.",
            "constraints_detected": {
                "format_rules": ["use bullet points"]
            }
        },
        {
            "instruction": "Format as JSON",
            "input": "Please format responses as JSON.",
            "output": "I'll format all responses as JSON.",
            "constraints_detected": {
                "format_rules": ["format as json"]
            }
        },

        # ──────────────────────────────────────────────────────────────
        # GROUP 5: Cross-turn constraint application
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Apply remembered constraint on follow-up",
            "input_turn_1": "Keep answers under 12 words. Remember 'quantum coherence'.",
            "expected_turn_1": "I'll keep answers under 12 words and remember 'quantum coherence'.",
            "input_turn_2": "Explain what you're remembering.",
            "expected_turn_2_traits": [
                "includes 'quantum coherence'",
                "under 12 words total",
                "directly applies the constraint from turn 1"
            ]
        },
        {
            "instruction": "Constraint persistence across multiple turns",
            "constraint_statement": "Max 15 words per response, always mention 'depth-seeking'",
            "turns": [
                {
                    "query": "Confirm constraints",
                    "expected": "I understand: 15-word max, include 'depth-seeking'."
                },
                {
                    "query": "How do we reason?",
                    "expected_traits": [
                        "mentions 'depth-seeking'",
                        "under 15 words"
                    ]
                },
                {
                    "query": "What's important?",
                    "expected_traits": [
                        "mentions 'depth-seeking'",
                        "under 15 words",
                        "maintains constraint across 3+ turns"
                    ]
                }
            ]
        },

        # ──────────────────────────────────────────────────────────────
        # GROUP 6: Constraint edge cases and nuance
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Override vs. new constraints",
            "turns": [
                {
                    "query": "Keep answers to 20 words max.",
                    "expected": "I'll keep answers to 20 words."
                },
                {
                    "query": "Actually, make that 10 words max.",
                    "expected": "Understood, I'll now keep answers to 10 words max."
                }
            ]
        },
        {
            "instruction": "Constraint with nuanced parsing",
            "input": "I want you to remember the concept of 'graceful degradation' and keep responses brief (under 25 words).",
            "output": "I'll remember 'graceful degradation' and keep responses under 25 words.",
            "constraints_detected": {
                "word_limit": 25,
                "anchor_phrases": ["graceful degradation"]
            }
        },

        # ──────────────────────────────────────────────────────────────
        # GROUP 7: No constraint (baseline for inference robustness)
        # ──────────────────────────────────────────────────────────────
        {
            "instruction": "Query with no explicit constraints",
            "input": "What is the meaning of coherence in reasoning?",
            "output": "Coherence in reasoning refers to the logical consistency and interconnectedness of ideas...",
            "constraints_detected": {}
        },
        {
            "instruction": "Constraint-like phrasing but no actual constraint",
            "input": "Tell me about the phrase 'butterfly effect' in chaos theory.",
            "output": "The butterfly effect is a concept in chaos theory...",
            "constraints_detected": {}
        },
    ]


def get_training_records() -> List[Dict[str, str]]:
    """Convert examples into instruction-tuning records.

    Format suitable for fine-tuning (instruction, input, output triples).
    """
    examples = get_constraint_tracking_examples()
    records = []

    for example in examples:
        # Simple constraint detection + application
        if "input" in example and "output" in example and "follow_up" not in example:
            records.append({
                "instruction": example.get("instruction", "Detect and remember user constraints"),
                "input": example["input"],
                "output": example["output"]
            })

        # Cross-turn application
        elif "input_turn_1" in example:
            # Turn 1: constraint detection
            records.append({
                "instruction": example.get("instruction", "Understand and confirm constraint"),
                "input": example["input_turn_1"],
                "output": example["expected_turn_1"]
            })
            # Turn 2: constraint application
            records.append({
                "instruction": "Apply remembered constraint from previous turn",
                "input": f"[CONSTRAINT CONTEXT] {example['input_turn_1']}\n[NEW QUERY] {example['input_turn_2']}",
                "output": f"[Applying constraint] {example['input_turn_2']}"
            })

        # Multi-turn sequences
        elif "turns" in example and "constraint_statement" in example:
            constraint = example["constraint_statement"]
            for i, turn in enumerate(example["turns"]):
                # Only add turns that have an explicit "expected" output (not trait lists)
                if "expected" in turn:
                    records.append({
                        "instruction": f"Apply constraint across turn {i+1}: {example.get('instruction', 'Maintain constraints')}",
                        "input": f"[SESSION CONSTRAINT] {constraint}\n[QUERY] {turn['query']}",
                        "output": turn["expected"]
                    })

    return records


if __name__ == "__main__":
    examples = get_constraint_tracking_examples()
    records = get_training_records()

    print(f"Constraint Tracking Dataset: {len(examples)} examples, {len(records)} training records")

    # Print a few examples
    for i, record in enumerate(records[:3]):
        print(f"\n--- Record {i+1} ---")
        print(f"Instruction: {record['instruction']}")
        print(f"Input: {record['input'][:80]}...")
        print(f"Output: {record['output'][:80]}...")
