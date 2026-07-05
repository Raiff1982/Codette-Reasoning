#!/usr/bin/env python3
"""OpenVINO inference backend for Codette.

Drop-in replacement for CodetteOrchestrator — exposes the same attributes
and methods that codette_forge_bridge.py and codette_server.py depend on:

  Attributes the forge bridge reads directly:
    orchestrator.available_adapters       list[str]
    orchestrator.verbose                  bool
    orchestrator._llm                     LLMShim (create_chat_completion compat)
    orchestrator._memory_kernel           optional memory kernel
    orchestrator.router                   AdapterRouter

  Methods the server/bridge call:
    orchestrator.route_and_generate(...)  → same dict shape as CodetteOrchestrator
    orchestrator.generate(...)            → (text, tokens, tool_log)
    orchestrator.set_memory_kernel(mk)    → wire memory into prompts
    orchestrator._build_memory_context()  → str

Adapter note:
    OpenVINO GenAI AdapterConfig requires .safetensors LoRA weights.
    Your GGUF adapters need conversion first — run:
        python openvino_backend/convert_adapters.py
    Without converted adapters, backend runs base-model-only (still GPU-accelerated).
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

# ── Path resolution ────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "inference"))

MODEL_DIR = _HERE / "llama-3.1-8b-instruct-int4"
ADAPTER_ST_DIR = _REPO / "adapters_safetensors"
BEHAVIORAL_ST_DIR = _REPO / "behavioral_safetensors"

ADAPTER_NAMES = [
    "newton", "davinci", "empathy", "philosophy", "quantum",
    "consciousness", "multi_perspective", "systems_architecture",
    "constraint_tracker", "orchestrator",
]

GEN_CONFIG = {
    "max_new_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.3,
}

SYNTHESIS_PERSPECTIVES = [
    "newton", "davinci", "empathy", "philosophy",
    "quantum", "consciousness", "multi_perspective", "systems_architecture",
]
FULL_SYNTHESIS_SENTINEL = "__all__"


# ── LLM shim — makes forge bridge fast-paths work unchanged ───────────────────

class _LLMShim:
    """Wraps OpenVINO LLMPipeline to expose create_chat_completion().

    The forge bridge calls self.orchestrator._llm.create_chat_completion()
    directly in the greeting and memory fast-paths. This shim intercepts those
    calls and routes them through OV GenAI so no bridge code needs changing.
    """

    def __init__(self, pipeline, format_fn, gen_config: dict):
        self._pipe = pipeline
        self._format = format_fn      # callable(system, user) -> prompt str
        self._cfg = gen_config

    def create_chat_completion(self, messages: list, max_tokens: int = 512,
                               temperature: float = 0.7, top_p: float = 0.9,
                               stop: list = None, **kwargs) -> dict:
        """Mimic llama_cpp Llama.create_chat_completion() return shape."""
        import openvino_genai as ov_genai

        system = ""
        user_parts = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                user_parts.append(m["content"])
            # assistant turns are flattened — OV GenAI single-turn for now

        user = "\n".join(user_parts)
        prompt = self._format(system, user)

        cfg = ov_genai.GenerationConfig()
        cfg.max_new_tokens = max_tokens
        cfg.temperature = temperature
        cfg.top_p = top_p
        cfg.repetition_penalty = self._cfg.get("repetition_penalty", 1.3)
        cfg.do_sample = True

        output = self._pipe.generate(prompt, cfg)
        text = str(output).strip()
        if text.startswith(prompt):
            text = text[len(prompt):].strip()

        tokens = len(text.split())
        return {
            "choices": [{"message": {"content": text, "role": "assistant"}}],
            "usage": {"completion_tokens": tokens, "prompt_tokens": 0, "total_tokens": tokens},
        }


# ── Main backend class ─────────────────────────────────────────────────────────

class OpenVINOBackend:
    """OpenVINO GenAI inference backend — drop-in for CodetteOrchestrator.

    Load once, adapter-switch per request via AdapterConfig.
    GPU (Arc iGPU) → CPU fallback on load failure.
    """

    def __init__(self, device: str = "AUTO", verbose: bool = False,
                 n_ctx: int = 8192, n_gpu_layers: int = 0,
                 memory_weighting=None):
        """
        Extra kwargs (n_ctx, n_gpu_layers, memory_weighting) accepted so the
        server can construct this with the same arguments it passes to
        CodetteOrchestrator — they are silently ignored where irrelevant.
        """
        self.device = device
        self.verbose = verbose
        self.memory_weighting = memory_weighting
        self.n_ctx = n_ctx          # kept for interface compatibility

        self._pipe = None
        self._ov = None
        self._llm: Optional[_LLMShim] = None
        self._memory_kernel = None
        self._adapter_paths: dict[str, Path] = {}

        if not MODEL_DIR.exists():
            raise FileNotFoundError(
                f"Converted model not found: {MODEL_DIR}\n"
                "Run: optimum-cli export openvino -m meta-llama/Llama-3.1-8B-Instruct "
                "--weight-format int4 --group-size 128 "
                "openvino_backend/llama-3.1-8b-instruct-int4"
            )

        self._discover_adapters()
        self._load_pipeline()

        # Wire AdapterRouter — same as CodetteOrchestrator
        from adapter_router import AdapterRouter
        self.router = AdapterRouter(
            available_adapters=self.available_adapters,
            memory_weighting=memory_weighting,
        )

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _discover_adapters(self):
        for name in ADAPTER_NAMES:
            behavioral = BEHAVIORAL_ST_DIR / f"{name}-behavioral-lora.safetensors"
            original = ADAPTER_ST_DIR / f"{name}-lora.safetensors"
            if behavioral.exists():
                self._adapter_paths[name] = behavioral
            elif original.exists():
                self._adapter_paths[name] = original

        if self._adapter_paths:
            print(f"[OV] Adapters: {', '.join(self._adapter_paths)}")
        else:
            print(
                "[OV] No safetensors adapters found — base model only.\n"
                f"     Convert with: python openvino_backend/convert_adapters.py"
            )

    @property
    def available_adapters(self) -> list:
        return list(self._adapter_paths.keys())

    def _load_pipeline(self):
        import traceback as _tb
        import openvino_genai as ov_genai
        self._ov = ov_genai

        print(f"[OV] MODEL_DIR={MODEL_DIR}", flush=True)
        print(f"[OV] MODEL_DIR exists={MODEL_DIR.exists()}", flush=True)
        print(f"[OV] Loading {MODEL_DIR.name} on {self.device}...", flush=True)
        t0 = time.time()
        try:
            self._pipe = ov_genai.LLMPipeline(str(MODEL_DIR), self.device)
        except Exception as e:
            print(f"[OV] {self.device} load FAILED: {e}", flush=True)
            _tb.print_exc()
            if self.device != "CPU":
                print(f"[OV] Retrying on CPU...", flush=True)
                try:
                    self._pipe = ov_genai.LLMPipeline(str(MODEL_DIR), "CPU")
                    self.device = "CPU"
                except Exception as e2:
                    print(f"[OV] CPU load also FAILED: {e2}", flush=True)
                    _tb.print_exc()
                    raise
            else:
                raise

        print(f"[OV] Loaded in {time.time()-t0:.1f}s on {self.device}", flush=True)
        self._llm = _LLMShim(self._pipe, self._format_chat, GEN_CONFIG)

    # ── Memory kernel (Phase 6 compatibility) ─────────────────────────────────

    def set_memory_kernel(self, memory_kernel):
        self._memory_kernel = memory_kernel

    def _build_memory_context(self) -> str:
        kernel = self._memory_kernel
        if not kernel or not getattr(kernel, 'memories', None):
            return ""
        try:
            important = kernel.recall_important(min_importance=7)
            if not important:
                return ""
            lines = [f"- {m.content}" for m in important[:10]]
            return "\n\nCore knowledge from your memory:\n" + "\n".join(lines)
        except Exception:
            return ""

    # ── Prompt formatting ──────────────────────────────────────────────────────

    def _format_chat(self, system: str, user: str) -> str:
        """Llama 3.1 instruct chat template."""
        return (
            "<|begin_of_text|>"
            "<|start_header_id|>system<|end_header_id|>\n\n"
            f"{system}"
            "<|eot_id|>"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            f"{user}"
            "<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
        )

    # ── Adapter config ─────────────────────────────────────────────────────────

    def _make_gen_config(self, adapter_name: Optional[str] = None,
                         max_tokens: int = 2048):
        cfg = self._ov.GenerationConfig()
        cfg.max_new_tokens = max_tokens
        cfg.temperature = GEN_CONFIG["temperature"]
        cfg.top_p = GEN_CONFIG["top_p"]
        cfg.repetition_penalty = GEN_CONFIG["repetition_penalty"]
        cfg.do_sample = True

        if adapter_name and adapter_name in self._adapter_paths:
            try:
                adapter_cfg = self._ov.AdapterConfig(
                    self._ov.Adapter(str(self._adapter_paths[adapter_name]))
                )
                cfg.adapters = adapter_cfg
            except Exception as e:
                if self.verbose:
                    print(f"[OV] Adapter {adapter_name} attach failed: {e}")

        return cfg

    # ── Core generate ──────────────────────────────────────────────────────────

    def generate(self, query: str, adapter_name: Optional[str] = None,
                 system_prompt: Optional[str] = None,
                 enable_tools: bool = False) -> tuple:
        """Generate response.  Returns (text, tokens, tool_log).

        Signature matches CodetteOrchestrator.generate() so forge bridge
        and server code works without modification.
        """
        from codette_shared import (
            ADAPTER_PROMPTS, extract_primary_user_query, extract_constraints,
            build_constraint_override, enforce_constraints,
        )
        try:
            from self_correction import universal_self_check
            _SC_AVAILABLE = True
        except ImportError:
            _SC_AVAILABLE = False

        if system_prompt is None:
            system_prompt = ADAPTER_PROMPTS.get(adapter_name, ADAPTER_PROMPTS["_base"])

        primary_query = extract_primary_user_query(query)
        constraints = extract_constraints(primary_query)
        constraint_override = build_constraint_override(constraints)

        # Integrity layer (complexity + role matching)
        _integrity_prefix = ""
        try:
            from reasoning_forge.response_complexity_matcher import ResponseComplexityMatcher
            from reasoning_forge.conversation_role_tracker import ConversationRoleTracker
            mode = ResponseComplexityMatcher().match(query)
            role_reading = ConversationRoleTracker().update(query)
            _integrity_prefix = (
                ResponseComplexityMatcher().get_system_prefix(mode) +
                ConversationRoleTracker().get_register_prefix(role_reading)
            )
        except Exception:
            pass

        full_system = ""
        if _integrity_prefix:
            full_system += _integrity_prefix
        if constraint_override:
            full_system += constraint_override
        full_system += system_prompt

        mem_ctx = self._build_memory_context()
        if mem_ctx:
            full_system += mem_ctx

        prompt = self._format_chat(full_system, query)
        cfg = self._make_gen_config(adapter_name)

        t0 = time.time()
        output = self._pipe.generate(prompt, cfg)
        elapsed = time.time() - t0

        text = str(output).strip()
        if text.startswith(prompt):
            text = text[len(prompt):].strip()

        if constraints:
            text = enforce_constraints(text, constraints)

        if _SC_AVAILABLE:
            text, _ = universal_self_check(text)

        tokens = len(text.split())
        tps = tokens / elapsed if elapsed > 0 else 0
        if self.verbose:
            print(f"  [OV:{adapter_name or 'base'}] ~{tokens} tok, {tps:.1f} tok/s")

        return text, tokens, []

    # ── Routing ────────────────────────────────────────────────────────────────

    def route_and_generate(self, query: str, max_adapters: int = 2,
                           strategy: str = "keyword",
                           force_adapter: Optional[str] = None) -> dict:
        """Route and generate.  Return dict matches CodetteOrchestrator output."""
        from adapter_router import RouteResult
        from codette_shared import (
            SYNTHESIS_PERSPECTIVES, FULL_SYNTHESIS_SENTINEL,
            extract_primary_user_query, ADAPTER_PROMPTS,
        )

        t0 = time.time()

        # ── Artist query intercept (hallucination prevention) ──────────────────
        import re
        query_lower = query.lower()
        _music_ctx = {'album', 'discography', 'band', 'artist', 'singer', 'genre', 'tour', 'concert', 'lyrics'}
        if any(w in query_lower.split() for w in _music_ctx):
            _artist_pats = [
                r'\b(who is|tell me about|what do you know about)\b.*\b(artist|singer|band|musician)\b',
                r'\b(album|discography|songs? by|music by)\s+[A-Z][a-z]',
            ]
            if any(re.search(p, query, re.IGNORECASE) for p in _artist_pats):
                return {
                    "response": (
                        "I don't have reliable information about specific artists. "
                        "Check Spotify, Wikipedia, or Bandcamp for accurate details.\n\n"
                        "I can help with production techniques, music theory, or sound design."
                    ),
                    "adapter": "uncertainty_aware",
                    "tokens": 0,
                    "time": 0.01,
                }

        # ── Full synthesis ─────────────────────────────────────────────────────
        if force_adapter == FULL_SYNTHESIS_SENTINEL:
            persp = [a for a in SYNTHESIS_PERSPECTIVES if a in self.available_adapters]
            perspectives = {}
            total_tokens = 0
            for name in persp:
                text, tokens, _ = self.generate(query, adapter_name=name)
                perspectives[name] = text
                total_tokens += tokens
            synthesis = self._synthesize(query, perspectives) if len(perspectives) > 1 \
                else (list(perspectives.values())[0] if perspectives else "")
            return {
                "response": synthesis,
                "perspectives": perspectives,
                "adapters": list(perspectives.keys()),
                "tokens": total_tokens,
                "time": time.time() - t0,
            }

        # ── Forced adapter ─────────────────────────────────────────────────────
        if force_adapter and force_adapter != "auto":
            text, tokens, _ = self.generate(query, adapter_name=force_adapter)
            self.router.record_use(force_adapter)
            return {
                "response": text,
                "adapter": force_adapter,
                "route": RouteResult(primary=force_adapter, confidence=1.0,
                                     reasoning="forced", strategy="forced"),
                "tokens": tokens,
                "time": time.time() - t0,
            }

        # ── Auto-route ─────────────────────────────────────────────────────────
        routing_query = extract_primary_user_query(query)
        route = self.router.route(routing_query, strategy=strategy,
                                  max_adapters=max_adapters)
        for a in route.all_adapters:
            self.router.record_use(a)

        print(f"\n  [OV] Route: {' + '.join(route.all_adapters)} "
              f"(conf={route.confidence:.2f}, {route.strategy})")

        if route.multi_perspective and len(route.all_adapters) > 1:
            perspectives = {}
            total_tokens = 0
            for name in route.all_adapters:
                if name not in self.available_adapters:
                    continue
                text, tokens, _ = self.generate(query, adapter_name=name)
                perspectives[name] = text
                total_tokens += tokens
            synthesis = self._synthesize(query, perspectives) if len(perspectives) > 1 \
                else (list(perspectives.values())[0] if perspectives else "")
            return {
                "response": synthesis,
                "perspectives": perspectives,
                "adapters": list(perspectives.keys()),
                "route": route,
                "tokens": total_tokens,
                "time": time.time() - t0,
            }

        text, tokens, _ = self.generate(query, adapter_name=route.primary)
        return {
            "response": text,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": time.time() - t0,
        }

    # ── Synthesis ──────────────────────────────────────────────────────────────

    def _synthesize(self, query: str, perspectives: dict) -> str:
        from codette_shared import ADAPTER_PROMPTS
        combined = "\n\n".join(
            f"[your {name} lens — internal note]\n{text[:1200]}"
            for name, text in perspectives.items()
        )
        synthesis_prompt = (
            f'A user asked: "{query}"\n\n'
            "Below are your own internal reasoning notes from several thinking lenses:\n\n"
            f"{combined}\n\n"
            "Write ONE unified answer in your own voice as Codette. "
            "Do NOT refer to named lenses. Answer the user's question directly.\n\nYour answer:"
        )
        text, _, _ = self.generate(
            synthesis_prompt,
            adapter_name=None,
            system_prompt=ADAPTER_PROMPTS["multi_perspective"],
        )
        return text

    # ── Diagnostics ────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "backend": "openvino",
            "model_dir": str(MODEL_DIR),
            "device": self.device,
            "model_loaded": self._pipe is not None,
            "adapters_available": self.available_adapters,
            "adapter_format": "safetensors",
        }
