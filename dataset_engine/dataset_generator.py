"""
Dataset Generator for Codette LoRA Training
=============================================

Main orchestrator that combines TemplateRegistry and AnswerGenerator
to produce chat-format JSONL files for fine-tuning Llama 3.1 8B
with LoRA adapters.

Features:
  - Deduplication: tracks all generated prompts to prevent duplicates
  - Reproducible: seed-based RNG for deterministic output
  - CLI interface: generate for one adapter or all adapters
  - Progress reporting: logs generation progress
  - Validation: checks output format before writing

Usage:
    python -m dataset_engine.dataset_generator --adapter newton --count 3000
    python -m dataset_engine.dataset_generator --all
    python -m dataset_engine.dataset_generator --adapter philosophy --count 2000 --seed 42
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Set

from dataset_engine.template_registry import TemplateRegistry
from dataset_engine.answer_generator import AnswerGenerator

logger = logging.getLogger("dataset_generator")


class DatasetGenerator:
    """Generates JSONL training datasets for Codette LoRA adapters."""

    def __init__(self, output_dir: str = "datasets", seed: Optional[int] = None):
        """Initialize the generator.

        Args:
            output_dir: Directory for output JSONL files.
            seed: Random seed for reproducibility. None for non-deterministic.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.registry = TemplateRegistry(seed=seed)
        self.answer_gen = AnswerGenerator(seed=seed)
        self._seen_questions: Set[str] = set()
        self._stats = {
            "total_generated": 0,
            "duplicates_skipped": 0,
            "counterexamples": 0,
        }

    def reset_dedup(self):
        """Clear the deduplication set (use between adapters)."""
        self._seen_questions.clear()

    def reset_stats(self):
        """Reset generation statistics."""
        self._stats = {
            "total_generated": 0,
            "duplicates_skipped": 0,
            "counterexamples": 0,
        }

    def generate_adapter(self, adapter: str,
                         count: Optional[int] = None) -> str:
        """Generate a JSONL dataset for a single adapter.

        Args:
            adapter: Adapter name (e.g. 'newton', 'philosophy').
            count: Number of examples to generate. Defaults to the
                   adapter's target size from the registry.

        Returns:
            Path to the generated JSONL file.
        """
        if adapter not in self.registry.get_adapter_names():
            raise ValueError(
                f"Unknown adapter '{adapter}'. "
                f"Available: {self.registry.get_adapter_names()}"
            )

        target = count or self.registry.get_target(adapter)
        output_path = self.output_dir / f"{adapter}_reasoning.jsonl"

        self.reset_dedup()
        self.reset_stats()

        logger.info(
            "Generating %d examples for adapter '%s' -> %s",
            target, adapter, output_path,
        )

        start_time = time.time()
        examples = []
        max_attempts = target * 5  # Safety valve against infinite loops
        attempts = 0

        while len(examples) < target and attempts < max_attempts:
            attempts += 1
            question, topic, subtopic, qtype = self.registry.sample_question(adapter)

            # Deduplicate
            q_normalized = question.strip().lower()
            if q_normalized in self._seen_questions:
                self._stats["duplicates_skipped"] += 1
                continue
            self._seen_questions.add(q_normalized)

            # Generate answer
            answer = self.answer_gen.generate(
                adapter=adapter,
                topic=topic,
                subtopic=subtopic,
                question=question,
                question_type=qtype,
            )

            # Validate answer quality
            if not self._validate_answer(answer):
                continue

            # Build chat-format message
            message = {
                "messages": [
                    {
                        "role": "system",
                        "content": self.registry.SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": question,
                    },
                    {
                        "role": "assistant",
                        "content": answer,
                    },
                ]
            }

            examples.append(message)

            if qtype == "counterexample":
                self._stats["counterexamples"] += 1

            self._stats["total_generated"] = len(examples)

            # Progress reporting
            if len(examples) > 0 and len(examples) % 500 == 0:
                elapsed = time.time() - start_time
                rate = len(examples) / elapsed if elapsed > 0 else 0
                logger.info(
                    "  [%s] %d / %d examples (%.1f/sec, %d duplicates skipped)",
                    adapter, len(examples), target, rate,
                    self._stats["duplicates_skipped"],
                )

        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        elapsed = time.time() - start_time
        counter_pct = (
            (self._stats["counterexamples"] / len(examples) * 100)
            if examples else 0
        )

        logger.info(
            "Completed '%s': %d examples in %.1fs "
            "(%.1f%% counterexamples, %d duplicates skipped)",
            adapter, len(examples), elapsed, counter_pct,
            self._stats["duplicates_skipped"],
        )

        if len(examples) < target:
            logger.warning(
                "Only generated %d / %d examples for '%s'. "
                "Consider expanding template pools.",
                len(examples), target, adapter,
            )

        return str(output_path)

    def generate_all(self) -> dict:
        """Generate datasets for all adapters.

        Returns:
            Dict mapping adapter names to output file paths.
        """
        results = {}
        total_start = time.time()

        for adapter in self.registry.get_adapter_names():
            try:
                path = self.generate_adapter(adapter)
                results[adapter] = path
            except Exception as e:
                logger.error("Failed to generate '%s': %s", adapter, e)
                results[adapter] = f"ERROR: {e}"

        total_elapsed = time.time() - total_start
        total_examples = sum(
            self._count_lines(p) for p in results.values()
            if not p.startswith("ERROR")
        )
        logger.info(
            "All adapters complete: %d total examples in %.1fs",
            total_examples, total_elapsed,
        )
        return results

    @staticmethod
    def _validate_answer(answer: str) -> bool:
        """Check that an answer meets minimum quality standards."""
        if not answer or not answer.strip():
            return False
        words = answer.split()
        if len(words) < 40:
            return False
        # Reject answers that are just the topic name repeated
        unique_words = set(w.lower() for w in words)
        if len(unique_words) < 20:
            return False
        return True

    @staticmethod
    def _count_lines(filepath: str) -> int:
        """Count lines in a file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except (OSError, IOError):
            return 0


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate JSONL training datasets for Codette LoRA adapters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m dataset_engine.dataset_generator --adapter newton --count 3000\n"
            "  python -m dataset_engine.dataset_generator --all\n"
            "  python -m dataset_engine.dataset_generator --all --seed 42\n"
            "  python -m dataset_engine.dataset_generator --adapter philosophy --output-dir ./my_datasets\n"
        ),
    )

    parser.add_argument(
        "--adapter",
        type=str,
        help="Adapter name to generate for (e.g. newton, philosophy).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate datasets for ALL adapters with their target sizes.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of examples to generate (overrides default target).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="datasets",
        help="Output directory for JSONL files (default: datasets).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible generation.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not args.adapter and not args.all:
        parser.error("Specify --adapter NAME or --all")

    generator = DatasetGenerator(
        output_dir=args.output_dir,
        seed=args.seed,
    )

    if args.all:
        results = generator.generate_all()
        print("\n--- Generation Summary ---")
        for adapter, path in results.items():
            if path.startswith("ERROR"):
                print(f"  {adapter}: {path}")
            else:
                count = generator._count_lines(path)
                print(f"  {adapter}: {count} examples -> {path}")
    else:
        path = generator.generate_adapter(args.adapter, args.count)
        count = generator._count_lines(path)
        print(f"\nGenerated {count} examples -> {path}")


if __name__ == "__main__":
    main()
