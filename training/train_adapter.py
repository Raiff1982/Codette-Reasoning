#!/usr/bin/env python3
"""
Codette LoRA Adapter Training Script
Hardware-adaptive version supporting:
CUDA (NVIDIA)
XPU (Intel Arc)
MPS (Apple)
CPU fallback
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from datasets import Dataset

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Ensure Intel SYCL runtime DLLs are discoverable for XPU support
_intel_bin = os.path.join(sys.prefix, "Lib", "site-packages", "Library", "bin")
if os.path.isdir(_intel_bin) and _intel_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _intel_bin + os.pathsep + os.environ.get("PATH", "")

import torch


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

def setup_logging(output_dir: str, adapter_name: str):
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"train_{adapter_name}_{timestamp}.log"

    logger = logging.getLogger(f"codette.train.{adapter_name}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        "%H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ------------------------------------------------------------
# DEVICE DETECTION
# ------------------------------------------------------------

def detect_vulkan_available():
    """Check if Vulkan compute is available (for non-PyTorch acceleration)."""
    try:
        import sys
        from pathlib import Path
        inference_dir = str(Path(__file__).parent.parent / "inference")
        if inference_dir not in sys.path:
            sys.path.insert(0, inference_dir)
        from vulkan_compute import is_vulkan_available
        return is_vulkan_available()
    except Exception:
        return False


def detect_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if detect_vulkan_available():
        return "vulkan"
    return "cpu"


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

def load_training_config(path=None):
    if path is None:
        path = Path(__file__).parent / "configs" / "default_training.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------
# DATASET
# ------------------------------------------------------------

def load_jsonl_dataset(dataset_path):
    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if "messages" not in obj:
                continue
            records.append(obj)
    return Dataset.from_list(records)


def format_chat_messages(example, tokenizer):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


# ------------------------------------------------------------
# MODEL LOADING
# ------------------------------------------------------------

def create_model_and_tokenizer(model_name, device, logger):
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    logger.info(f"Loading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {
        "trust_remote_code": True,
        "use_cache": False,
    }

    # ---------------- Intel XPU — streaming file I/O loading ----------------
    # Arc 140V: 8GB VRAM (too small for 16GB bf16 model), BnB is CUDA-only.
    # from_pretrained/load_checkpoint_and_dispatch/safe_open all use mmap → OOM.
    # Fix: read safetensors binary format with plain open()+read(), no mmap.
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

    # ---------------- CUDA ----------------
    if device == "cuda":
        logger.info("CUDA GPU detected — using 4-bit QLoRA")
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs["quantization_config"] = bnb
        model_kwargs["device_map"] = "auto"
        model_kwargs["dtype"] = torch.bfloat16

    # ---------------- Apple GPU ----------------
    elif device == "mps":
        logger.info("Apple MPS backend detected")
        model_kwargs["dtype"] = torch.float16

    # ---------------- CPU fallback ----------------
    else:
        logger.warning("CPU detected — enabling low memory mode")
        model_kwargs["device_map"] = {"": "cpu"}
        model_kwargs["low_cpu_mem_usage"] = True
        model_kwargs["dtype"] = torch.float16

    logger.info("Loading model")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        **model_kwargs
    )

    if device == "mps":
        model = model.to("mps")

    model.gradient_checkpointing_enable()
    return model, tokenizer


# ------------------------------------------------------------
# LORA
# ------------------------------------------------------------

def apply_lora_config(model, lora_cfg, logger):
    from peft import LoraConfig, get_peft_model, TaskType

    config = LoraConfig(
        r=lora_cfg["rank"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(
        f"LoRA applied: {trainable:,}/{total:,} trainable params"
    )
    return model


# ------------------------------------------------------------
# TRAIN
# ------------------------------------------------------------

def train(model, tokenizer, dataset, train_cfg, output_dir, logger):
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

    logger.info("Training started")
    result = trainer.train()

    final_dir = os.path.join(output_dir, "final")
    trainer.save_model(final_dir)
    tokenizer.save_pretrained(final_dir)
    logger.info("Training finished")

    return result


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--adapter-name", required=True)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    config = load_training_config(args.config)
    model_cfg = config["model"]
    lora_cfg = config["lora"]
    train_cfg = config["training"]
    output_cfg = config["output"]

    output_dir = os.path.join(
        output_cfg["base_dir"],
        args.adapter_name
    )

    logger = setup_logging(output_dir, args.adapter_name)
    device = detect_device()
    logger.info(f"Device: {device}")

    raw_dataset = load_jsonl_dataset(args.dataset)
    model, tokenizer = create_model_and_tokenizer(
        model_cfg["name"],
        device,
        logger
    )

    cpu_workers = max(1, os.cpu_count() - 1)
    logger.info(f"Tokenizing dataset with {cpu_workers} workers")
    formatted_dataset = raw_dataset.map(
        lambda ex: format_chat_messages(ex, tokenizer),
        remove_columns=raw_dataset.column_names,
        num_proc=cpu_workers,
        desc="Tokenizing dataset",
    )

    model = apply_lora_config(model, lora_cfg, logger)

    result = train(
        model,
        tokenizer,
        formatted_dataset,
        train_cfg,
        output_dir,
        logger
    )

    logger.info(
        f"Training complete (loss={result.training_loss:.4f})"
    )


if __name__ == "__main__":
    main()
