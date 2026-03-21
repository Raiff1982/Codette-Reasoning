#!/usr/bin/env python3
"""
Codette Shared-Model Batch Adapter Training
--------------------------------------------
Loads the base model ONCE and trains multiple LoRA adapters
sequentially without reloading the 8B model.

Major benefits
--------------
* Eliminates repeated model loads
* Prevents GPU memory fragmentation
* Speeds multi-adapter training
* More stable on 8GB GPUs
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import os
import yaml
import torch

os.environ["TOKENIZERS_PARALLELISM"] = "false"


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"shared_training_{ts}.log"

    logger = logging.getLogger("codette.shared_train")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        "%H:%M:%S"
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------
# Device Detection
# ---------------------------------------------------------

def detect_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ---------------------------------------------------------
# Config Loaders
# ---------------------------------------------------------

def load_adapter_registry(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["adapters"]


def load_training_defaults(path=None):
    if path is None:
        path = Path("configs/default_training.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------
# Dataset Loader
# ---------------------------------------------------------

def load_jsonl_dataset(path):
    from datasets import Dataset
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if "messages" in obj:
                rows.append(obj)
    return Dataset.from_list(rows)


def format_chat_messages(example, tokenizer):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


# ---------------------------------------------------------
# Base Model Loader
# ---------------------------------------------------------

def load_base_model(model_name, device, logger):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logger.info("Loading tokenizer")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- XPU: streaming file I/O loading (no mmap, avoids OOM) ---
    if device == "xpu":
        logger.info("Intel Arc — streaming CPU load (no mmap, minimal peak memory)")

        import ctypes
        import gc
        import struct as _struct
        from accelerate import init_empty_weights
        from accelerate.utils import set_module_tensor_to_device
        from huggingface_hub import snapshot_download
        from transformers import AutoConfig

        checkpoint_dir = snapshot_download(model_name)
        logger.info(f"Checkpoint: {checkpoint_dir}")
        gc.collect()

        model_config = AutoConfig.from_pretrained(
            model_name, trust_remote_code=True
        )
        with init_empty_weights():
            model = AutoModelForCausalLM.from_config(
                model_config, trust_remote_code=True
            )

        _dt = {
            "BF16": torch.bfloat16, "F16": torch.float16,
            "F32": torch.float32, "F64": torch.float64,
            "I64": torch.int64, "I32": torch.int32,
            "I16": torch.int16, "I8": torch.int8,
            "U8": torch.uint8, "BOOL": torch.bool,
        }

        shard_files = sorted(Path(checkpoint_dir).glob("*.safetensors"))
        logger.info(f"Loading {len(shard_files)} shards via streaming I/O")

        for i, shard_file in enumerate(shard_files):
            logger.info(f"  Shard {i+1}/{len(shard_files)}: {shard_file.name}")
            with open(shard_file, "rb") as fp:
                header_size = _struct.unpack("<Q", fp.read(8))[0]
                header = json.loads(fp.read(header_size))
                data_start = 8 + header_size
                for name, meta in header.items():
                    if name == "__metadata__":
                        continue
                    start, end = meta["data_offsets"]
                    nbytes = end - start
                    buf = bytearray(nbytes)
                    fp.seek(data_start + start)
                    fp.readinto(buf)
                    tensor = torch.frombuffer(
                        buf, dtype=_dt[meta["dtype"]]
                    ).reshape(meta["shape"])
                    set_module_tensor_to_device(
                        model, name, "cpu",
                        value=tensor, dtype=torch.bfloat16,
                    )
                    del buf, tensor
            gc.collect()
            try:
                k32 = ctypes.windll.kernel32
                k32.SetProcessWorkingSetSize(k32.GetCurrentProcess(), -1, -1)
            except Exception:
                pass
            logger.info(f"  Shard {i+1}/{len(shard_files)}: done")

        model.tie_weights()
        model.gradient_checkpointing_enable()
        return model, tokenizer

    # --- All other devices ---
    logger.info("Loading base model (once)")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    model.gradient_checkpointing_enable()
    return model, tokenizer


# ---------------------------------------------------------
# Apply LoRA
# ---------------------------------------------------------

def attach_lora(model, lora_cfg, logger):
    from peft import LoraConfig, get_peft_model, TaskType

    config = LoraConfig(
        r=lora_cfg["rank"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"],
        task_type=TaskType.CAUSAL_LM,
        bias="none"
    )
    logger.info("Attaching LoRA adapter")
    model = get_peft_model(model, config)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Trainable params: {trainable:,}/{total:,}"
    )
    return model


def detach_lora(model):
    return model.base_model


# ---------------------------------------------------------
# Training
# ---------------------------------------------------------

def train_adapter(model, tokenizer, dataset, train_cfg, output_dir):
    from transformers import TrainingArguments
    from trl import SFTTrainer

    device = next(model.parameters()).device
    use_bf16 = device.type in ("cuda", "xpu")
    use_fp16 = device.type == "mps"

    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=train_cfg["epochs"],
        per_device_train_batch_size=train_cfg["batch_size"],
        gradient_accumulation_steps=train_cfg["gradient_accumulation_steps"],
        learning_rate=train_cfg["learning_rate"],
        warmup_ratio=train_cfg.get("warmup_ratio", 0.03),
        logging_steps=train_cfg["logging_steps"],
        save_steps=train_cfg["save_steps"],
        fp16=use_fp16,
        bf16=use_bf16,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=train_cfg["max_seq_length"],
    )

    result = trainer.train()
    trainer.save_model(output_dir)
    return result


# ---------------------------------------------------------
# Main Training Loop
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="configs/adapter_registry.yaml"
    )
    args = parser.parse_args()

    logger = setup_logging()
    registry = load_adapter_registry(args.registry)
    defaults = load_training_defaults()
    device = detect_device()
    logger.info(f"Device detected: {device}")

    model_cfg = defaults["model"]
    lora_cfg = defaults["lora"]
    train_cfg = defaults["training"]

    # -----------------------------------------------------
    # Load model ONCE
    # -----------------------------------------------------
    model, tokenizer = load_base_model(
        model_cfg["name"],
        device,
        logger
    )

    # -----------------------------------------------------
    # Train adapters sequentially
    # -----------------------------------------------------
    for name, cfg in registry.items():
        logger.info("")
        logger.info(f"===== TRAINING ADAPTER: {name} =====")

        dataset_path = cfg["dataset"]
        raw_dataset = load_jsonl_dataset(dataset_path)

        cpu_workers = max(1, os.cpu_count() - 1)
        logger.info(f"Tokenizing with {cpu_workers} workers")
        dataset = raw_dataset.map(
            lambda ex: format_chat_messages(ex, tokenizer),
            remove_columns=raw_dataset.column_names,
            num_proc=cpu_workers,
            desc=f"Tokenizing {name}",
        )

        model = attach_lora(model, lora_cfg, logger)

        out_dir = Path("adapters") / name
        out_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        result = train_adapter(
            model,
            tokenizer,
            dataset,
            train_cfg,
            str(out_dir)
        )
        elapsed = time.time() - start

        logger.info(
            f"{name} complete — loss {result.training_loss:.4f} "
            f"in {elapsed:.1f}s"
        )

        model = detach_lora(model)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch, "xpu") and torch.xpu.is_available():
            torch.xpu.empty_cache()


if __name__ == "__main__":
    main()
