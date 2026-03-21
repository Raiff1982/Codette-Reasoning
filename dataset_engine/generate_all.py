#!/usr/bin/env python3
"""
Generate All Codette Training Datasets
========================================

Batch script that generates JSONL datasets for ALL LoRA adapters
with their configured target sizes. Outputs to:
    J:/codette-training-lab/datasets/{adapter_name}_reasoning.jsonl

Adapter targets:
    newton ............... 3000 examples
    davinci .............. 2500 examples
    empathy .............. 2500 examples
    philosophy ........... 2000 examples
    quantum .............. 2000 examples
    consciousness ........ 3000 examples
    multi_perspective .... 2500 examples
    systems_architecture . 2000 examples
    -----------------------------------
    Total ................ 20,500 examples

Usage:
    python generate_all.py
    python generate_all.py --seed 42
    python generate_all.py --seed 42 --output-dir J:/codette-training-lab/datasets
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure the parent directory is on the path so imports work
# when running this script directly.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from dataset_engine.template_registry import TemplateRegistry
from dataset_engine.dataset_generator import DatasetGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate all Codette training datasets.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible generation (default: 42).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_DIR / "datasets"),
        help="Output directory for JSONL files.",
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
    logger = logging.getLogger("generate_all")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Codette Dataset Generation Engine")
    logger.info("=" * 60)
    logger.info("Output directory: %s", output_dir)
    logger.info("Random seed: %s", args.seed)

    # Show targets
    registry = TemplateRegistry(seed=args.seed)
    total_target = 0
    logger.info("")
    logger.info("Adapter targets:")
    for adapter in registry.get_adapter_names():
        target = registry.get_target(adapter)
        total_target += target
        logger.info("  %-25s %5d examples", adapter, target)
    logger.info("  %-25s %5d examples", "TOTAL", total_target)
    logger.info("")

    # Generate
    generator = DatasetGenerator(
        output_dir=str(output_dir),
        seed=args.seed,
    )

    start_time = time.time()
    results = generator.generate_all()
    total_elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)

    total_examples = 0
    all_ok = True
    for adapter in registry.get_adapter_names():
        path = results.get(adapter, "ERROR: NOT GENERATED")
        if path.startswith("ERROR"):
            status = f"FAILED: {path}"
            all_ok = False
        else:
            count = generator._count_lines(path)
            total_examples += count
            target = registry.get_target(adapter)
            pct = (count / target * 100) if target > 0 else 0
            status = f"{count:5d} / {target:5d} ({pct:.0f}%) -> {path}"
        print(f"  {adapter:25s}  {status}")

    print(f"\n  {'TOTAL':25s}  {total_examples:5d} / {total_target:5d} examples")
    print(f"  {'Time':25s}  {total_elapsed:.1f} seconds")
    rate = total_examples / total_elapsed if total_elapsed > 0 else 0
    print(f"  {'Rate':25s}  {rate:.0f} examples/sec")
    print("=" * 60)

    # Validate output files
    print("\nValidating output files...")
    validation_ok = True
    for adapter in registry.get_adapter_names():
        path = results.get(adapter)
        if not path or path.startswith("ERROR"):
            continue
        try:
            errors = _validate_jsonl(path)
            if errors:
                print(f"  {adapter}: {len(errors)} validation errors")
                for err in errors[:3]:
                    print(f"    - {err}")
                validation_ok = False
            else:
                print(f"  {adapter}: OK")
        except Exception as e:
            print(f"  {adapter}: Validation failed: {e}")
            validation_ok = False

    if validation_ok and all_ok:
        print("\nAll datasets generated and validated successfully.")
    else:
        print("\nSome issues detected. Check logs above.")
        sys.exit(1)


def _validate_jsonl(filepath: str, sample_size: int = 50) -> list:
    """Validate a JSONL file for correct format.

    Checks:
      - Each line is valid JSON
      - Each record has a 'messages' key
      - Messages contain system, user, and assistant roles
      - No empty content fields

    Returns list of error strings (empty = valid).
    """
    errors = []
    line_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line_count += 1
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: Invalid JSON: {e}")
                continue

            if "messages" not in record:
                errors.append(f"Line {i}: Missing 'messages' key")
                continue

            messages = record["messages"]
            if not isinstance(messages, list) or len(messages) != 3:
                errors.append(f"Line {i}: Expected 3 messages, got {len(messages) if isinstance(messages, list) else 'non-list'}")
                continue

            roles = [m.get("role") for m in messages]
            if roles != ["system", "user", "assistant"]:
                errors.append(f"Line {i}: Expected roles [system, user, assistant], got {roles}")
                continue

            for m in messages:
                content = m.get("content", "")
                if not content or not content.strip():
                    errors.append(f"Line {i}: Empty content for role '{m.get('role')}'")

            # Only check a sample of lines for detailed validation
            if i > sample_size and not errors:
                break

    if not errors and line_count == 0:
        errors.append("File is empty")

    return errors


if __name__ == "__main__":
    main()
