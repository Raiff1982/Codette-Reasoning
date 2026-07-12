#!/usr/bin/env python3
"""Real semantic embedder for the perspective web — OpenVINO feature extraction.

Loads a small sentence-embedding model (all-MiniLM-L6-v2, 384-d) via
optimum.intel as OpenVINO IR, mean-pools over the attention mask, L2-normalizes.
This is what turns the perspective web from LEXICAL to SEMANTIC: node distance
becomes real meaning-space distance, not shared-vocabulary overlap.

Design choices, deliberate:
  - CPU by default (CODETTE_EMBED_DEVICE overrides). The INT4 LLM already owns
    the Arc iGPU's shared UMA memory; a ~80MB embedder on CPU avoids contention.
  - Lazy process-wide singleton; first call exports HF -> OV IR and caches it to
    models/minilm-ov so later starts are instant and offline.
  - Exposes .encode(text) -> np.ndarray so it drops straight into
    SemanticTensionEngine(llama_model=<this>) with zero changes there.
  - If it cannot load (offline + no cache), get_semantic_embedder() returns None
    and the caller stays in lexical mode. Never fabricates, never breaks a turn.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np

_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
_OV_DIR = Path(__file__).resolve().parent.parent / "models" / "minilm-ov"
_DEVICE = os.environ.get("CODETTE_EMBED_DEVICE", "CPU")


class OVSemanticEmbedder:
    """Sentence embedder with a Llama-style .encode(text) surface."""

    def __init__(self) -> None:
        from optimum.intel import OVModelForFeatureExtraction
        from transformers import AutoTokenizer

        if _OV_DIR.exists():
            self.model = OVModelForFeatureExtraction.from_pretrained(str(_OV_DIR), device=_DEVICE)
            self.tok = AutoTokenizer.from_pretrained(str(_OV_DIR))
        else:
            # First run: export HF -> OpenVINO IR, then cache to disk.
            self.model = OVModelForFeatureExtraction.from_pretrained(
                _MODEL_ID, export=True, device=_DEVICE)
            self.tok = AutoTokenizer.from_pretrained(_MODEL_ID)
            try:
                _OV_DIR.mkdir(parents=True, exist_ok=True)
                self.model.save_pretrained(str(_OV_DIR))
                self.tok.save_pretrained(str(_OV_DIR))
            except Exception:
                pass  # caching is best-effort; embeddings still work this session

    def encode(self, text: str) -> np.ndarray:
        """Mean-pooled, L2-normalized sentence embedding, shape (384,)."""
        import torch

        inputs = self.tok(text or " ", return_tensors="pt", truncation=True,
                          max_length=256, padding=True)
        with torch.no_grad():
            out = self.model(**inputs)
        last = out.last_hidden_state                    # (1, T, 384)
        mask = inputs["attention_mask"].unsqueeze(-1).to(last.dtype)  # (1, T, 1)
        summed = (last * mask).sum(dim=1)               # (1, 384)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        emb = (summed / counts)[0].cpu().numpy().astype(np.float32)
        norm = float(np.linalg.norm(emb))
        return emb / norm if norm > 1e-8 else emb


_INSTANCE: Optional[OVSemanticEmbedder] = None
_TRIED = False


def get_semantic_embedder():
    """Lazy singleton. Returns a SemanticTensionEngine wrapping the OV embedder,
    or None if it can't load (caller falls back to lexical mode)."""
    global _INSTANCE, _TRIED
    if _INSTANCE is not None:
        return _INSTANCE
    if _TRIED:
        return None
    _TRIED = True
    try:
        raw = OVSemanticEmbedder()
        _ = raw.encode("warmup")  # prove it actually runs before returning it
        from reasoning_forge.semantic_tension import SemanticTensionEngine
        _INSTANCE = SemanticTensionEngine(llama_model=raw)
        print(f"[EMBED] semantic embedder ready (all-MiniLM-L6-v2, {_DEVICE})", flush=True)
        return _INSTANCE
    except Exception as e:
        print(f"[EMBED] semantic embedder unavailable, staying lexical: "
              f"{type(e).__name__}: {str(e)[:120]}", flush=True)
        return None
