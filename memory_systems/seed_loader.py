"""
SeedLoader — warm-start memory for Codette sessions.

Loads curated cocoon JSON files into a LivingMemoryKernel (or SemanticCocoonField)
before the first user turn.  Eliminates the cold-start context gap where Codette
doesn't know who Jonathan is, what its core values are, or what domain it's in.

Seed files live in cocoons/ and follow the lightweight schema:
  { title, emotion/emotional_tag, summary/content, quote, moment, tags }

Domain seeds (music_production, code_reasoning, etc.) are loaded on top of core
seeds when the session has a known domain.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Absolute path to cocoons/ relative to this file's location
_COCOONS_DIR = Path(__file__).parent.parent / "cocoons"

# Core seeds always loaded — identity, values, creator bond
CORE_SEEDS = [
    "cocoon_identity.json",
    "cocoon_current_state.json",
    "cocoon_jonathan.json",
    "cocoon_honesty.json",
    "cocoon_perspectives.json",
    "cocoon_conversation.json",
]

# Domain seeds loaded when domain is known
DOMAIN_SEEDS: dict[str, list[str]] = {
    "music_production": ["domain_music_production.json"],
    "empathy":          ["cocoon_compassion.json", "cocoon_sorrow.json"],
    "creativity":       ["cocoon_joy.json", "cocoon_curiosity.json"],
    "fear_uncertainty": ["cocoon_fear.json"],
}

# Seeds are identity/value foundations — must clear the min_importance=7 threshold
# in CodetteOrchestrator._build_memory_context() to reach the LLM system prompt.
SEED_IMPORTANCE = 7


def _normalize_cocoon(data: dict) -> dict:
    """
    Normalize seed JSON schema to MemoryCocoon kwargs.
    Handles both 'emotion' and 'emotional_tag' field names.
    """
    return {
        "title":        data.get("title", "Seed"),
        "content":      data.get("summary") or data.get("content", ""),
        "emotional_tag": data.get("emotion") or data.get("emotional_tag", "neutral"),
        "importance":   data.get("importance", SEED_IMPORTANCE),
    }


def load_seeds(
    memory,
    domain: Optional[str] = None,
    cocoons_dir: Optional[Path] = None,
) -> int:
    """
    Load seed cocoons into a memory object.

    Works with both LivingMemoryKernel and SemanticCocoonField —
    detects which store() signature to use.

    Args:
        memory:       LivingMemoryKernel or SemanticCocoonField instance
        domain:       Optional domain name (see DOMAIN_SEEDS keys)
        cocoons_dir:  Override path to cocoons directory

    Returns:
        Number of seeds loaded
    """
    base = Path(cocoons_dir) if cocoons_dir else _COCOONS_DIR
    files = list(CORE_SEEDS)
    if domain and domain in DOMAIN_SEEDS:
        files.extend(DOMAIN_SEEDS[domain])

    loaded = 0
    for fname in files:
        fpath = base / fname
        if not fpath.exists():
            logger.debug(f"[SeedLoader] Seed not found, skipping: {fpath}")
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"[SeedLoader] Failed to read {fname}: {e}")
            continue

        kwargs = _normalize_cocoon(data)
        _store(memory, kwargs)
        loaded += 1
        logger.debug(f"[SeedLoader] Loaded: {kwargs['title']}")

    logger.info(f"[SeedLoader] Warm start complete — {loaded} seeds loaded (domain={domain or 'none'})")
    return loaded


def _store(memory, kwargs: dict):
    """Dispatch to the correct store method depending on memory type."""
    # SemanticCocoonField
    try:
        from memory_systems.semantic_cocoon_field import SemanticCocoon
        if hasattr(memory, "store") and hasattr(memory, "_cocoons"):
            import time, hashlib
            ts = time.time()
            anchor = hashlib.sha256(
                f"{kwargs['title']}{ts}{kwargs['content']}".encode()
            ).hexdigest()
            cocoon = SemanticCocoon(**kwargs, timestamp=ts, anchor=anchor)
            memory.store(cocoon)
            return
    except ImportError:
        pass

    # LivingMemoryKernelV2 — needs MemoryCocoonV2 (has age_hours, epsilon_band, etc.)
    try:
        from reasoning_forge.living_memory_v2 import LivingMemoryKernelV2, MemoryCocoonV2
        if isinstance(memory, LivingMemoryKernelV2):
            import time, hashlib
            ts = time.time()
            anchor = hashlib.sha256(
                f"{kwargs['title']}{ts}{kwargs['content']}".encode()
            ).hexdigest()
            cocoon = MemoryCocoonV2(
                title=kwargs["title"],
                content=kwargs["content"],
                emotional_tag=kwargs.get("emotional_tag", "neutral"),
                importance=kwargs.get("importance", SEED_IMPORTANCE),
                timestamp=ts,
                anchor=anchor,
            )
            memory.store(cocoon)
            return
    except ImportError:
        pass

    # LivingMemoryKernel v1 (reasoning_forge or memory_systems)
    try:
        from reasoning_forge.memory_kernel import MemoryCocoon
    except ImportError:
        from memory_systems.codette_memory_kernel import MemoryCocoon

    cocoon = MemoryCocoon(**kwargs)
    memory.store(cocoon)


def warm_start(memory, domain: Optional[str] = None) -> int:
    """Convenience alias for load_seeds."""
    return load_seeds(memory, domain=domain)
