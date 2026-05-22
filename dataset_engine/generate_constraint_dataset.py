#!/usr/bin/env python3
"""Generate constraint-tracking training dataset in JSONL format."""

import json
from pathlib import Path

# Add project root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataset_engine.constraint_tracking_dataset import get_training_records


def main():
    """Generate and save constraint tracking dataset."""
    output_file = Path(__file__).parent.parent / "data" / "constraint_tracking.jsonl"
    output_file.parent.mkdir(exist_ok=True)

    records = get_training_records()

    print(f"Generating constraint tracking dataset: {len(records)} records")

    with open(output_file, "w") as f:
        for i, record in enumerate(records):
            # Format as instruction-tuning record
            obj = {
                "instruction": record["instruction"],
                "input": record["input"] if record.get("input") else "",
                "output": record["output"]
            }
            f.write(json.dumps(obj) + "\n")

    print(f"Saved to {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")

    # Verify
    with open(output_file) as f:
        count = sum(1 for _ in f)
    print(f"Verified: {count} lines in JSONL file")


if __name__ == "__main__":
    main()
