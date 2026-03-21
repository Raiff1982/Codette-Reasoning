#!/usr/bin/env python3
"""
Codette LoRA Adapter Merger
==============================

Merge one or more LoRA adapters into the base model to produce
a standalone fine-tuned model. Adapters are applied and merged
sequentially in the order specified.

Usage:
    python -m training.merge_adapters \
        --base-model meta-llama/Llama-3.1-8B-Instruct \
        --adapters adapters/newton/final adapters/davinci/final \
        --output merged_model

    python -m training.merge_adapters \
        --base-model meta-llama/Llama-3.1-8B-Instruct \
        --adapters adapters/rcxi/final \
        --output merged_model \
        --dtype bfloat16
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import torch


def setup_logging(output_dir: str) -> logging.Logger:
    """Configure logging for the merge process.

    Args:
        output_dir: Directory for log output.

    Returns:
        Configured logger instance.
    """
    log_dir = Path(output_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("codette.merge")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(
        str(log_dir / f"merge_{timestamp}.log"), encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(ch)

    return logger


def resolve_dtype(dtype_str: str) -> torch.dtype:
    """Convert a string dtype to a torch dtype.

    Args:
        dtype_str: One of 'float32', 'float16', 'bfloat16'.

    Returns:
        Corresponding torch.dtype.

    Raises:
        ValueError: If the string is not a recognized dtype.
    """
    dtype_map = {
        "float32": torch.float32,
        "fp32": torch.float32,
        "float16": torch.float16,
        "fp16": torch.float16,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
    }
    if dtype_str not in dtype_map:
        raise ValueError(
            f"Unknown dtype: {dtype_str}. "
            f"Choose from: {list(dtype_map.keys())}"
        )
    return dtype_map[dtype_str]


def validate_adapter_paths(adapter_paths: list[str], logger: logging.Logger) -> None:
    """Validate that all adapter paths exist and contain expected files.

    Args:
        adapter_paths: List of adapter directory paths.
        logger: Logger instance.

    Raises:
        FileNotFoundError: If any adapter path is invalid.
    """
    for adapter_path in adapter_paths:
        path = Path(adapter_path)
        if not path.exists():
            raise FileNotFoundError(f"Adapter directory not found: {adapter_path}")

        # Check for adapter_config.json (PEFT marker)
        config_file = path / "adapter_config.json"
        if not config_file.exists():
            raise FileNotFoundError(
                f"No adapter_config.json found in {adapter_path}. "
                f"Is this a valid PEFT adapter directory?"
            )

        logger.info(f"Validated adapter: {adapter_path}")


def load_base_model(
    model_name: str,
    dtype: torch.dtype,
    device_map: str,
    logger: logging.Logger,
):
    """Load the base model for merging.

    Args:
        model_name: HuggingFace model identifier.
        dtype: Torch dtype for model weights.
        device_map: Device map strategy.
        logger: Logger instance.

    Returns:
        Tuple of (model, tokenizer).
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logger.info(f"Loading base model: {model_name}")
    logger.info(f"  dtype: {dtype}, device_map: {device_map}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True,
    )

    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"Base model loaded: {param_count:,} parameters")

    return model, tokenizer


def apply_and_merge_adapter(
    model,
    adapter_path: str,
    adapter_index: int,
    total_adapters: int,
    logger: logging.Logger,
):
    """Apply a single LoRA adapter and merge it into the base weights.

    Uses PEFT's load_adapter, set_adapter, and merge_and_unload
    to apply LoRA weights directly into the base model.

    Args:
        model: The current model (base or previously merged).
        adapter_path: Path to the PEFT adapter directory.
        adapter_index: Index of this adapter (for logging).
        total_adapters: Total number of adapters to merge.
        logger: Logger instance.

    Returns:
        Model with the adapter merged in.
    """
    from peft import PeftModel

    adapter_name = Path(adapter_path).parent.name
    logger.info(
        f"[{adapter_index}/{total_adapters}] "
        f"Applying adapter: {adapter_name} ({adapter_path})"
    )

    # Load adapter config to log details
    config_path = Path(adapter_path) / "adapter_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        adapter_config = json.load(f)

    lora_rank = adapter_config.get("r", "unknown")
    lora_alpha = adapter_config.get("lora_alpha", "unknown")
    target_modules = adapter_config.get("target_modules", [])

    logger.info(
        f"  LoRA config: rank={lora_rank}, alpha={lora_alpha}, "
        f"modules={target_modules}"
    )

    # Load and merge
    if adapter_index == 1:
        # First adapter: wrap model with PeftModel
        model = PeftModel.from_pretrained(
            model,
            adapter_path,
            is_trainable=False,
        )
    else:
        # Subsequent adapters: load as named adapter
        adapter_id = f"adapter_{adapter_index}"
        model.load_adapter(adapter_path, adapter_name=adapter_id)
        model.set_adapter(adapter_id)

    # Merge adapter weights into base model
    logger.info(f"  Merging adapter weights into base model...")
    model = model.merge_and_unload()

    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"  Merged successfully. Model params: {param_count:,}")

    return model


def save_merged_model(
    model,
    tokenizer,
    output_dir: str,
    logger: logging.Logger,
) -> None:
    """Save the fully merged model and tokenizer.

    Args:
        model: The merged model.
        tokenizer: The tokenizer.
        output_dir: Directory to save the model.
        logger: Logger instance.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving merged model to: {output_dir}")

    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    # Calculate total size
    total_size = 0
    for f in output_path.glob("*.safetensors"):
        total_size += f.stat().st_size
    for f in output_path.glob("*.bin"):
        total_size += f.stat().st_size

    size_gb = total_size / (1024 ** 3)
    logger.info(f"Model saved: {size_gb:.2f} GB")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Merge LoRA adapters into the base model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="meta-llama/Llama-3.1-8B-Instruct",
        help="Base model to merge adapters into",
    )
    parser.add_argument(
        "--adapters",
        nargs="+",
        required=True,
        help="Paths to PEFT adapter directories (applied in order)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for merged model",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="bfloat16",
        choices=["float32", "fp32", "float16", "fp16", "bfloat16", "bf16"],
        help="Model dtype for merging",
    )
    parser.add_argument(
        "--device-map",
        type=str,
        default="auto",
        help="Device map strategy (auto, cpu, cuda:0, etc.)",
    )
    return parser.parse_args()


def main():
    """Main entry point for adapter merging."""
    args = parse_args()

    logger = setup_logging(args.output)
    logger.info("=== Codette LoRA Adapter Merger ===")
    logger.info(f"Base model: {args.base_model}")
    logger.info(f"Adapters to merge ({len(args.adapters)}): {args.adapters}")
    logger.info(f"Output: {args.output}")
    logger.info(f"dtype: {args.dtype}")

    dtype = resolve_dtype(args.dtype)

    # Validate adapters
    try:
        validate_adapter_paths(args.adapters, logger)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    start_time = time.time()

    try:
        # Load base model
        model, tokenizer = load_base_model(
            args.base_model, dtype, args.device_map, logger
        )

        # Apply and merge each adapter sequentially
        for i, adapter_path in enumerate(args.adapters, 1):
            model = apply_and_merge_adapter(
                model=model,
                adapter_path=adapter_path,
                adapter_index=i,
                total_adapters=len(args.adapters),
                logger=logger,
            )

        # Save merged model
        save_merged_model(model, tokenizer, args.output, logger)

        elapsed = time.time() - start_time

        # Save merge metadata
        metadata = {
            "base_model": args.base_model,
            "adapters_merged": args.adapters,
            "adapter_count": len(args.adapters),
            "dtype": args.dtype,
            "merge_time_seconds": elapsed,
            "timestamp": datetime.now().isoformat(),
        }
        metadata_path = Path(args.output) / "merge_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"=== Merge complete in {elapsed:.1f}s ===")
        logger.info(f"Merged model saved to: {args.output}")

    except Exception as e:
        logger.error(f"Merge failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
