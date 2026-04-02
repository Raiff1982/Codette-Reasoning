#!/usr/bin/env python3
"""Portable runtime/bootstrap helpers for Codette inference entry points."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INFERENCE_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL_FILENAME = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"


def _existing_paths(paths: List[Path]) -> List[Path]:
    return [path for path in paths if path.exists()]


def candidate_site_packages() -> List[Path]:
    env_path = os.environ.get("CODETTE_SITE_PACKAGES")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend([
        PROJECT_ROOT / ".venv" / "Lib" / "site-packages",
        PROJECT_ROOT / ".venv" / "lib" / "python3.12" / "site-packages",
        PROJECT_ROOT / ".venv" / "lib" / "python3.11" / "site-packages",
        PROJECT_ROOT / ".venv" / "lib" / "python3.10" / "site-packages",
        Path(r"J:\Lib\site-packages"),
    ])
    return _existing_paths(candidates)


def runtime_pythonpath_entries(include_inference_dir: bool = True) -> List[str]:
    entries: List[str] = []
    for site_path in candidate_site_packages():
        entries.append(str(site_path))

    if include_inference_dir:
        entries.append(str(INFERENCE_DIR))
    entries.append(str(PROJECT_ROOT))

    inherited = os.environ.get("PYTHONPATH", "")
    for raw in inherited.split(os.pathsep):
        raw = raw.strip()
        if raw:
            entries.append(raw)

    deduped: List[str] = []
    seen = set()
    for entry in entries:
        if entry not in seen:
            seen.add(entry)
            deduped.append(entry)
    return deduped


def bootstrap_environment(include_inference_dir: bool = True) -> Dict[str, Optional[str]]:
    """Apply portable import/path bootstrapping."""
    selected_site = None
    for site_path in candidate_site_packages():
        site_str = str(site_path)
        if site_str not in sys.path:
            sys.path.insert(0, site_str)
        selected_site = selected_site or site_str

        bin_candidate = site_path / "Library" / "bin"
        if bin_candidate.exists():
            os.environ["PATH"] = str(bin_candidate) + os.pathsep + os.environ.get("PATH", "")

    if include_inference_dir:
        inference_str = str(INFERENCE_DIR)
        if inference_str not in sys.path:
            sys.path.insert(0, inference_str)

    project_str = str(PROJECT_ROOT)
    if project_str not in sys.path:
        sys.path.insert(0, project_str)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    return {
        "project_root": project_str,
        "site_packages": selected_site,
        "inference_dir": str(INFERENCE_DIR),
    }


def resolve_model_path(default_name: str = DEFAULT_MODEL_FILENAME) -> Path:
    env_path = os.environ.get("CODETTE_MODEL_PATH")
    if env_path:
        return Path(env_path)
    return PROJECT_ROOT / "models" / "base" / default_name


def resolve_adapter_dir() -> Path:
    return Path(os.environ.get("CODETTE_ADAPTER_DIR", str(PROJECT_ROOT / "models" / "adapters")))


def resolve_behavioral_adapter_dir() -> Path:
    return Path(
        os.environ.get(
            "CODETTE_BEHAVIORAL_DIR",
            str(PROJECT_ROOT / "behavioral-lora-f16-gguf"),
        )
    )


def resolve_ollama_models_dir() -> Path:
    env_path = os.environ.get("OLLAMA_MODELS") or os.environ.get("CODETTE_OLLAMA_MODELS")
    if env_path:
        return Path(env_path)
    return PROJECT_ROOT / ".ollama"


def resolve_python_executable() -> str:
    env_path = os.environ.get("CODETTE_PYTHON_EXE")
    if env_path:
        return env_path

    if sys.executable:
        return sys.executable

    for candidate in ("python3", "python"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return "python3"


def resolve_allowed_roots() -> List[Path]:
    roots = [PROJECT_ROOT]
    docs = Path.home() / "Documents"
    if docs.exists():
        roots.append(docs)
    extra = os.environ.get("CODETTE_ALLOWED_ROOTS", "")
    for raw in extra.split(os.pathsep):
        raw = raw.strip()
        if raw:
            roots.append(Path(raw))
    return roots
