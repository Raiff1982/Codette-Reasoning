#!/usr/bin/env python3
"""Download recommended Codette models and adapters via huggingface-cli."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def ensure_cli() -> None:
    if shutil.which("huggingface-cli"):
        return
    raise SystemExit("huggingface-cli not found. Install huggingface-hub first: pip install huggingface-hub")


def run(cmd: list[str]) -> int:
    print("[models]", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download Codette models and adapters.")
    parser.add_argument("--cpu", action="store_true", help="Also download the lightweight CPU model.")
    parser.add_argument("--f16", action="store_true", help="Also download the higher-quality F16 model.")
    args = parser.parse_args(argv)

    ensure_cli()

    commands = [
        [
            "huggingface-cli", "download",
            "Raiff1982/codette-llama-3.1-8b-gguf",
            "--include", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            "--local-dir", "models/base/",
        ],
        [
            "huggingface-cli", "download",
            "Raiff1982/codette-lora-adapters",
            "--include", "behavioral-gguf/*",
            "--local-dir", "behavioral-lora-f16-gguf/",
        ],
    ]

    if args.cpu:
        commands.append([
            "huggingface-cli", "download",
            "Raiff1982/Llama-3.2-1B-Instruct-Q8",
            "--include", "llama-3.2-1b-instruct-q8_0.gguf",
            "--local-dir", "models/base/",
        ])

    if args.f16:
        commands.append([
            "huggingface-cli", "download",
            "Raiff1982/Meta-Llama-3.1-8B-Instruct-F16",
            "--include", "Meta-Llama-3.1-8B-Instruct.F16.gguf",
            "--local-dir", "models/base/",
        ])

    for command in commands:
        code = run(command)
        if code != 0:
            return code

    print("[models] download complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
