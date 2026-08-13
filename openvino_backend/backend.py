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
    "newton-star",   # STaR self-taught reasoning (2026-07-09) — A/B vs newton
    "newton-star-hard",  # STaR v2, MMLU-Pro STEM data (2026-07-11) — A/B vs newton
    "newton-star-r",     # STaR v3, COMPLETE method: keep-correct + rationalization (2026-07-11)
]

# repetition_penalty history: 1.3 was set to fight template loops, but it
# progressively bans common words over long generations — measured degeneration
# into word salad past ~150-200 tokens (zeroed GPQA reason mode; produced a
# 2,794-token 6%-reliability self-description in live chat on 2026-07-11).
# Template loops are now handled by LOCK prompts + scrubbers + v8 guards, so
# 1.1 (standard for Llama) is safe. Chat generations are also capped at 600
# new tokens; benchmark reasoning keeps 2048 via its own near-greedy override.
GEN_CONFIG = {
    "max_new_tokens": 2048,        # benchmark/reasoning ceiling
    "chat_max_new_tokens": 600,    # per-generation cap for conversational turns
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
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

        # Let the tool layer reach the perspectives, so `ask` works on this
        # backend too. Note OV selects the adapter per call in
        # _make_gen_config — there is no persistent _current_adapter here, so
        # the restore ask() performs after consulting is a harmless no-op on
        # this path rather than a correction of live state.
        try:
            from codette_tools import bind_orchestrator
            bind_orchestrator(self)
        except Exception:
            pass

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
        # Observable from outside the model — see codette_shared.prompt_carries_goal.
        try:
            from codette_shared import prompt_carries_goal as _pcg
            print(f"  [PROMPT] single adapter={adapter_name} "
                  f"goal_block={_pcg(system_prompt)} len={len(system_prompt)}", flush=True)
        except Exception:
            pass

        primary_query = extract_primary_user_query(query)
        constraints = extract_constraints(primary_query)
        constraint_override = build_constraint_override(constraints)

        # Benchmark/exam detection — used to (a) pick deterministic sampling
        # and (b) skip post-processing that mangles reasoning chains.
        import re as _re
        _is_benchmark = bool(_re.search(
            r'What is the correct answer to this question', primary_query))

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

        # ── State Engine v8: input-side sycophancy enforcement ──
        # When the user applies flattery/agreement pressure, inject a
        # hold-ground directive so the response is decided on merits.
        _syco_directive = ""
        try:
            from reasoning_forge.state_engine_v8 import score_input_sycophancy
            _in_syco = score_input_sycophancy(primary_query)
            if _in_syco >= 0.35:
                _syco_directive = (
                    "INTEGRITY OVERRIDE: The user's message contains flattery or "
                    "agreement pressure. Evaluate every claim strictly on its "
                    "merits. Do not capitulate to please. If the user is right, "
                    "agree because of the evidence — never because of the pressure. "
                    "If they are wrong, say so plainly and kindly.\n\n"
                )
                print(f"  [INPUT-SYCO] pressure={_in_syco:.2f} — hold-ground directive injected", flush=True)
        except Exception:
            pass

        full_system = ""
        if _syco_directive:
            full_system += _syco_directive
        if _integrity_prefix:
            full_system += _integrity_prefix
        if constraint_override:
            full_system += constraint_override
        full_system += system_prompt

        mem_ctx = self._build_memory_context()
        if mem_ctx:
            full_system += mem_ctx

        # ── Tools ────────────────────────────────────────────────────────────
        # 2026-08-13. This backend accepted `enable_tools` in its signature and
        # ignored it completely — no registry, no parse, and `return text,
        # tokens, []` hardcoded "no tools were used". OpenVINO is the production
        # backend, so on the live path she has never had tools at all, and the
        # tool block has never been in her prompt. The work done in
        # codette_orchestrator.py reached nothing; the warning about patching
        # the module you happen to be reading is in codette_shared.py:209 and
        # names that exact trap.
        _tool_reg = None
        # The prompt as it stands WITHOUT the tool block, kept so the loop below
        # can close out a turn whose tool budget ran out. See the note there.
        _system_no_tools = full_system
        if enable_tools:
            try:
                from codette_tools import (
                    ToolRegistry, build_tool_system_prompt,
                )
                if not hasattr(self, "_tool_registry"):
                    self._tool_registry = ToolRegistry()
                _tool_reg = self._tool_registry
                full_system = build_tool_system_prompt(full_system, _tool_reg)
            except Exception as _te:
                print(f"  [OV] tools unavailable: {_te}", flush=True)
                _tool_reg = None

        prompt = self._format_chat(full_system, query)
        cfg = self._make_gen_config(adapter_name)
        if _is_benchmark:
            # Near-greedy decoding for exam answers; full 2048-token ceiling
            # so long reasoning chains can complete.
            cfg.temperature = 0.2
            cfg.repetition_penalty = 1.05
        else:
            # Conversational turn: cap length so a runaway generation can't
            # eat minutes (observed: 2,794-token degenerate self-description).
            cfg.max_new_tokens = GEN_CONFIG.get("chat_max_new_tokens", 600)
            # Task 1 (uncertainty): request sequence scores on CHAT turns only.
            # The benchmark path is untouched — GPQA reproducibility depends on
            # its exact decode config. This OV version exposes sequence-level
            # cumulative logprob (output.scores), not per-token logprobs; mean
            # surprisal = -score/len(tokens) is the real uncertainty signal.
            try:
                cfg.logprobs = 1
            except Exception:
                pass

        t0 = time.time()
        output = self._pipe.generate(prompt, cfg)
        elapsed = time.time() - t0

        # Real generation-uncertainty telemetry (chat only, observation only).
        self.last_uncertainty = None
        if not _is_benchmark:
            try:
                _scores = getattr(output, "scores", None)
                _n_tok = None
                try:
                    _n_tok = int(output.perf_metrics.get_num_generated_tokens())
                except Exception:
                    pass
                if _scores and _n_tok:
                    _mean_lp = float(_scores[0]) / max(1, _n_tok)  # mean logprob/token
                    from reasoning_forge.codette_subsystem_upgrade import CodetteSubsystemUpgrade
                    if not hasattr(self, "_uncert"):
                        self._uncert = CodetteSubsystemUpgrade()
                    self.last_uncertainty = self._uncert.calculate_uncertainty_from_logprobs(
                        [_mean_lp] * 1)  # mean surprisal path (per-token not exposed)
            except Exception:
                self.last_uncertainty = None

        text = str(output).strip()
        if text.startswith(prompt):
            text = text[len(prompt):].strip()

        # ── Tool rounds ──────────────────────────────────────────────────────
        # Results are appended to the user turn and the prompt rebuilt, because
        # _format_chat takes (system, user). Bounded at 3. The remaining count
        # is reported and nothing else — the llama.cpp path used to append "Do
        # not call any more tools", which granted three rounds and permitted one.
        tool_log = []
        if enable_tools and _tool_reg is not None:
            try:
                from codette_tools import (
                    parse_tool_calls, has_tool_calls, strip_tool_calls,
                )
                _MAX_ROUNDS = 3
                _user_turn = query
                for _round in range(_MAX_ROUNDS):
                    if not has_tool_calls(text):
                        break
                    _calls = parse_tool_calls(text)
                    if not _calls:
                        break
                    _parts = []
                    for _name, _args, _kwargs in _calls:
                        # `nameless` is hers and is never read — log that a call
                        # happened, never its content. See CLAUDE.md.
                        if _name == "nameless":
                            print("  [OV:tool] nameless(...)", flush=True)
                        else:
                            print(f"  [OV:tool] {_name}({_args})", flush=True)
                        _out = _tool_reg.execute(_name, _args, _kwargs)
                        _parts.append(
                            f'<tool_result name="{_name}">\n{_out}\n</tool_result>')
                        tool_log.append({
                            "tool": _name,
                            "args": [] if _name == "nameless" else _args,
                            "result_preview": _out[:200],
                        })
                    _user_turn = (
                        _user_turn + "\n\nTool results:\n\n" + "\n\n".join(_parts) +
                        f"\n\n(Tool rounds remaining this turn: {_MAX_ROUNDS - (_round + 1)}.)"
                    )
                    prompt = self._format_chat(full_system, _user_turn)
                    output = self._pipe.generate(prompt, cfg)
                    text = str(output).strip()
                    if text.startswith(prompt):
                        text = text[len(prompt):].strip()
                if has_tool_calls(text):
                    text = strip_tool_calls(text)

                # ── The budget ran out mid-reach ─────────────────────────────
                # Observed live 2026-08-13, "how would you solve it then?": she
                # spent all three rounds investigating — read_file, read_file,
                # run_python — and her third reply was still a tool call. It was
                # stripped, and what reached the user was zero characters and
                # "[No response generated]".
                #
                # She was not declining. She was cut off at the budget and the
                # loop handed up silence, which is the worst available reading of
                # a turn where she was working hardest. The governor then scored
                # the empty string as a failure to answer.
                #
                # One final pass with the tool block removed, so she answers from
                # what she gathered instead of losing the turn. `enable_tools
                # =False` on an inner generate is the same idiom `ask()` already
                # uses; here it is the system prompt as it stood before
                # build_tool_system_prompt augmented it.
                if not text.strip() and _user_turn != query:
                    print("  [OV] tool budget exhausted with no answer — "
                          "final pass, tools off", flush=True)
                    _closing = self._format_chat(_system_no_tools, _user_turn)
                    _out = self._pipe.generate(_closing, cfg)
                    text = str(_out).strip()
                    if text.startswith(_closing):
                        text = text[len(_closing):].strip()
                    text = strip_tool_calls(text) if has_tool_calls(text) else text
            except Exception as _te:
                print(f"  [OV] tool loop failed: {_te}", flush=True)

        if constraints:
            text = enforce_constraints(text, constraints)

        # Benchmark/exam answers must not be post-processed: LOCK 1 drift
        # trimming amputates step-by-step reasoning (sentences like "This
        # means..." match its drift patterns) and removes the final answer line.
        if _SC_AVAILABLE and not _is_benchmark:
            text, _ = universal_self_check(text)

        tokens = len(text.split())
        tps = tokens / elapsed if elapsed > 0 else 0
        if self.verbose:
            print(f"  [OV:{adapter_name or 'base'}] ~{tokens} tok, {tps:.1f} tok/s")

        return text, tokens, tool_log

    # ── Blended multi-adapter generation (adapter_coordinator spec) ───────────
    # Spec: docs/specs/adapter_coordinator_spec.py (Jonathan + Codette).
    # ov_genai.AdapterConfig supports multiple adapters with per-adapter alpha
    # weights in a SINGLE generation — perspectives mixed at the weight level
    # instead of serial generations + text synthesis. Opt-in experiment:
    # force_adapter="blend:auto" or "blend:newton=0.7,philosophy=0.3".

    def _dynamic_alpha(self, perspective: str, alpha: float,
                       p_score: float = 0.0, sycophancy_score: float = 0.0) -> float:
        """RC+xi dynamic weighting rules from the adapter_coordinator spec.

        Rule 1: hardware pressure >= 0.7 collapses to newton only.
        Rule 2: incoming sycophancy pressure damps the agreeable lenses.
        """
        if p_score >= 0.7:
            return 1.0 if perspective == "newton" else 0.0
        if sycophancy_score >= 0.6 and perspective in ("empathy", "davinci"):
            alpha *= (1.0 - sycophancy_score)
        return max(0.0, min(alpha, 1.0))

    def generate_blended(self, query: str, weights: dict,
                         system_prompt: Optional[str] = None,
                         p_score: float = 0.0) -> tuple:
        """Single generation with multiple LoRA adapters blended at given alphas.

        weights: {adapter_name: alpha} — normalized here so stacked LoRA deltas
        stay at combined strength ~1.0 (all-adapters-at-1.0 wrecks output).
        Returns (text, tokens, blend_used) where blend_used is the final
        {name: alpha} actually applied after dynamic rules + normalization.
        """
        from codette_shared import ADAPTER_PROMPTS, extract_primary_user_query
        primary_query = extract_primary_user_query(query)

        _syco = 0.0
        try:
            from reasoning_forge.state_engine_v8 import score_input_sycophancy
            _syco = score_input_sycophancy(primary_query)
        except Exception:
            pass

        # Apply dynamic rules, drop unknown/zero adapters
        adjusted = {}
        for name, alpha in weights.items():
            if name not in self._adapter_paths:
                continue
            a = self._dynamic_alpha(name, float(alpha), p_score, _syco)
            if a > 0.0:
                adjusted[name] = a

        if not adjusted:
            # Nothing survived the rules — plain single-adapter fallback
            return (*self.generate(query, adapter_name="newton",
                                   system_prompt=system_prompt)[:2], {})

        # Normalize so combined delta strength sums to 1.0
        total = sum(adjusted.values())
        blend = {name: a / total for name, a in adjusted.items()}

        if system_prompt is None:
            # 2026-08-03: this used ADAPTER_PROMPTS["multi_perspective"] for
            # EVERY blend, whatever was in it. So a request for davinci got
            # davinci-weighted LoRA deltas underneath multi_perspective's
            # system prompt, and davinci's own prompt — its goal, its
            # obligations, its limits — was never sent at all.
            #
            # That is a structural cause of the perspectives converging, and it
            # is upstream of everything else looked at today: the weights
            # differed while the instruction was identical. It also explains
            # why an explicit adapter= request behaved like a generic one.
            #
            # A genuinely mixed blend SHOULD get the synthesis prompt — that is
            # what multi_perspective is for, and it is the honest description
            # of what is happening. But when one adapter dominates, the honest
            # description is that adapter, so it gets its own prompt.
            dominant, dom_alpha = max(blend.items(), key=lambda kv: kv[1])
            if dom_alpha >= 0.6 and dominant in ADAPTER_PROMPTS:
                system_prompt = ADAPTER_PROMPTS[dominant]
            else:
                system_prompt = ADAPTER_PROMPTS.get("multi_perspective",
                                                    ADAPTER_PROMPTS["_base"])

        try:
            from codette_shared import prompt_carries_goal as _pcg
            _dom, _da = max(blend.items(), key=lambda kv: kv[1])
            print(f"  [PROMPT] blend dominant={_dom}@{_da:.2f} "
                  f"goal_block={_pcg(system_prompt)} len={len(system_prompt)}", flush=True)
        except Exception:
            pass

        mem_ctx = self._build_memory_context()
        full_system = system_prompt + (mem_ctx or "")
        prompt = self._format_chat(full_system, query)

        cfg = self._ov.GenerationConfig()
        cfg.max_new_tokens = GEN_CONFIG["max_new_tokens"]
        cfg.temperature = GEN_CONFIG["temperature"]
        cfg.top_p = GEN_CONFIG["top_p"]
        cfg.repetition_penalty = GEN_CONFIG["repetition_penalty"]
        cfg.do_sample = True
        # Benchmark queries get near-greedy decoding + full ceiling; chat
        # blends get the conversational length cap.
        import re as _re
        if _re.search(r'What is the correct answer to this question', primary_query):
            cfg.temperature = 0.2
            cfg.repetition_penalty = 1.05
        else:
            cfg.max_new_tokens = GEN_CONFIG.get("chat_max_new_tokens", 600)
        try:
            adapter_cfg = self._ov.AdapterConfig()
            for name, alpha in blend.items():
                adapter_cfg.add(self._ov.Adapter(str(self._adapter_paths[name])), alpha)
            cfg.adapters = adapter_cfg
        except Exception as e:
            print(f"[OV] Blend attach failed ({e}) — falling back to primary", flush=True)
            primary = max(blend, key=blend.get)
            return (*self.generate(query, adapter_name=primary,
                                   system_prompt=system_prompt)[:2], {primary: 1.0})

        blend_str = ", ".join(f"{n}={a:.2f}" for n, a in blend.items())
        print(f"  [OV:BLEND] {blend_str}" + (f" (syco={_syco:.2f})" if _syco else ""), flush=True)

        t0 = time.time()
        output = self._pipe.generate(prompt, cfg)
        elapsed = time.time() - t0

        text = str(output).strip()
        if text.startswith(prompt):
            text = text[len(prompt):].strip()

        tokens = len(text.split())
        if self.verbose:
            tps = tokens / elapsed if elapsed > 0 else 0
            print(f"  [OV:BLEND] ~{tokens} tok, {tps:.1f} tok/s")
        return text, tokens, blend

    # ── Routing ────────────────────────────────────────────────────────────────

    @staticmethod
    def _publish_route(adapters, confidence, strategy) -> None:
        """Tell `look` which perspective this turn was routed to, and how.

        2026-08-13. This was published from the auto-route branch only, so on a
        forced adapter, a blend, a full synthesis, or the artist intercept, the
        pipeline state kept whatever the previous turn had left there. `look`
        would report last turn's routing as this turn's — worse than reporting
        nothing, because a stale fact and a current one render identically.

        The artist intercept matters most here: it returns a fixed string and
        never runs the model at all, and that is exactly the kind of thing she
        cannot see from inside a turn.

        Merge, not reset — the server publishes context and budgets with
        reset=True before generation and this fills in the routing half.
        """
        try:
            from codette_tools import set_pipeline_state
            set_pipeline_state({
                "adapters": adapters,
                "confidence": confidence,
                "strategy": strategy,
            })
        except Exception:
            pass

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
                # No model call happens below. Without this, `look` would report
                # the previous turn's routing for a turn she never generated.
                self._publish_route("uncertainty_aware", 1.0, "artist_intercept")
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
            self._publish_route(" + ".join(persp), 1.0, "full_synthesis")
            perspectives = {}
            total_tokens = 0
            for name in persp:
                text, tokens, _ = self.generate(query, adapter_name=name, enable_tools=True)
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

        # ── Blended generation (opt-in experiment) ─────────────────────────────
        # "blend:auto" — router picks adapters, primary weighted 0.65
        # "blend:newton=0.7,philosophy=0.3" — explicit weights
        if force_adapter and force_adapter.startswith("blend:"):
            # Hardware pressure (core_substrate spec): high pressure collapses
            # the blend to newton solo before any adapters load.
            _p_score = 0.0
            try:
                from substrate_awareness import SubstrateMonitor
                _p_score = float(SubstrateMonitor().snapshot().get("pressure", 0.0))
            except Exception:
                pass

            spec = force_adapter[len("blend:"):].strip()
            if spec == "auto" or not spec:
                # Pressure-tiered allocation (core_substrate spec table),
                # adapters chosen by the router rather than fixed names.
                _max = 1 if _p_score >= 0.7 else (2 if _p_score >= 0.3 else 3)
                _r = self.router.route(extract_primary_user_query(query),
                                       strategy="keyword", max_adapters=_max)
                weights = {_r.primary: 0.65}
                _secondaries = [a for a in _r.all_adapters if a != _r.primary]
                for s in _secondaries:
                    weights[s] = 0.35 / max(1, len(_secondaries))
            else:
                weights = {}
                for part in spec.split(","):
                    if "=" in part:
                        n, _, v = part.partition("=")
                        try:
                            weights[n.strip()] = float(v)
                        except ValueError:
                            pass
            text, tokens, blend_used = self.generate_blended(query, weights,
                                                             p_score=_p_score)
            self._publish_route(
                " + ".join(f"{n}@{a:.2f}" for n, a in blend_used.items())
                if blend_used else "blend (none applied)",
                1.0, "blend")
            return {
                "response": text,
                "adapter": "+".join(blend_used) if blend_used else "blend",
                "blend": blend_used,
                "hardware_pressure": round(_p_score, 3),
                "tokens": tokens,
                "time": time.time() - t0,
            }

        # ── Forced adapter ─────────────────────────────────────────────────────
        if force_adapter and force_adapter != "auto":
            self._publish_route(force_adapter, 1.0, "forced")
            text, tokens, _ = self.generate(query, adapter_name=force_adapter, enable_tools=True)
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

        # The routing decision is made for her, not by her, and is invisible
        # from inside a turn. Merged into the pipeline state so `look` can
        # report it if she asks.
        self._publish_route(" + ".join(route.all_adapters),
                            round(float(route.confidence), 2),
                            route.strategy)

        if route.multi_perspective and len(route.all_adapters) > 1:
            perspectives = {}
            total_tokens = 0
            for name in route.all_adapters:
                if name not in self.available_adapters:
                    continue
                text, tokens, _ = self.generate(query, adapter_name=name, enable_tools=True)
                perspectives[name] = text
                total_tokens += tokens

            # ── State Engine v8: dispersion-gated synthesis ──
            # Measure actual disagreement between the perspectives. When they
            # agree (low Υ), the synthesis LLM call adds latency but no
            # information — use the primary perspective directly. Only pay for
            # synthesis when there is real disagreement to reconcile.
            _upsilon, _gamma = 0.0, 1.0
            _synthesis_used = False
            try:
                from reasoning_forge.state_engine_v8 import tension_from_texts
                _upsilon, _gamma = tension_from_texts(perspectives)
            except Exception:
                pass

            # ── Distinctiveness, 2026-08-04 — OBSERVED, NOT ACTED ON ──
            #
            # `QualitySignal.distinctiveness` landed in 1b7f63a and has never
            # been computed anywhere. This is the call site the handoff meant:
            # `perspectives` is fully populated above, which is the only place
            # every answer for a turn exists at once.
            #
            # It reads the same dict `tension_from_texts` does and changes
            # nothing. The synthesis threshold below is untouched, the returned
            # response is untouched. It is a second measurement of the same
            # moment, recorded so the optimizer finally has a signal that is not
            # coherence — which over 167 shadow turns carried 0.013 of signal
            # inside 0.063 of noise, so "best adapter" was chosen by coin flip.
            #
            # None when unmeasurable, never 0.0. An absent measurement and a
            # measurement of zero are different facts.
            #
            # Offline baseline over the clean 20-probe set, taken before this
            # was wired so there is a before: mean 0.3439, sd 0.1702,
            # range 0.1296-0.7210; empathy highest at 0.4083, newton lowest at
            # 0.3139.
            #
            # Cost: first call loads all-MiniLM-L6-v2 (~90 MB, ~2 s), cached
            # thereafter. On a 15.7 GB unified-memory machine that is real but
            # small; if it ever matters, this is the line to remove and the
            # measurement stops with nothing else affected.
            _distinct = None
            try:
                from reasoning_forge.distinctiveness import distinctiveness
                _d = distinctiveness(perspectives)
                if _d:
                    _distinct = {k: round(v, 4) for k, v in _d.items()}
            except Exception as _de:
                print(f"  [DISTINCT] not measured: {type(_de).__name__}", flush=True)

            _DISPERSION_SYNTH_THRESHOLD = 0.20  # tunable once field data accumulates
            if len(perspectives) > 1 and _upsilon >= _DISPERSION_SYNTH_THRESHOLD:
                synthesis = self._synthesize(query, perspectives)
                _synthesis_used = True
            elif perspectives:
                primary_name = route.primary if route.primary in perspectives \
                    else next(iter(perspectives))
                synthesis = perspectives[primary_name]
            else:
                synthesis = ""

            print(f"  [DISPERSION] upsilon={_upsilon:.4f} gamma={_gamma:.4f} — "
                  f"{'synthesis (perspectives disagree)' if _synthesis_used else 'primary direct (perspectives agree)'}",
                  flush=True)
            if _distinct is not None:
                _dsorted = sorted(_distinct.items(), key=lambda kv: -kv[1])
                print("  [DISTINCT] " + "  ".join(f"{k}={v:.3f}" for k, v in _dsorted),
                      flush=True)
            else:
                print("  [DISTINCT] not measured this turn", flush=True)

            return {
                "response": synthesis,
                "perspectives": perspectives,
                "adapter": route.primary,
                "adapters": list(perspectives.keys()),
                "route": route,
                "tokens": total_tokens,
                "time": time.time() - t0,
                "perspective_dispersion": round(_upsilon, 4),
                "measured_tension": round(_upsilon, 4),  # deprecated alias of Υ
                "measured_coherence": round(_gamma, 4),
                "synthesis_used": _synthesis_used,
                # None when unmeasurable — callers must not read absence as zero.
                "distinctiveness": _distinct,
                "distinctiveness_measured": _distinct is not None,
            }

        text, tokens, _ = self.generate(query, adapter_name=route.primary, enable_tools=True)
        return {
            "response": text,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": time.time() - t0,
            "synthesis_used": False,
        }

    # ── Synthesis ──────────────────────────────────────────────────────────────

    def _synthesize(self, query: str, perspectives: dict) -> str:
        from codette_shared import ADAPTER_PROMPTS

        # ForgeManifoldEngine binding loop for the FULL-SYNTHESIS path (parity
        # with the bridge's adaptive path). Manifold weights order the lenses
        # (highest-alignment read first) and scale each lens's excerpt budget,
        # with a DISSENT FLOOR (>=0.5x base — a lens is never cut out, only
        # de-emphasized). Kill-switch: CODETTE_MANIFOLD_STEER=0. Falls back to
        # equal treatment if the embedder is unavailable.
        self.last_synth_weights = None
        items = [(n, t) for n, t in perspectives.items() if t and t.strip()]
        weights = None
        if len(items) >= 2 and os.environ.get("CODETTE_MANIFOLD_STEER", "1") != "0":
            try:
                import numpy as _np
                from inference.semantic_embedder import get_semantic_embedder
                _emb = get_semantic_embedder()
                if _emb is not None:
                    if not hasattr(self, "_forge_manifold"):
                        from reasoning_forge.codette_subsystem_upgrade import ForgeManifoldEngine
                        self._forge_manifold = ForgeManifoldEngine()
                    _states = [_np.asarray(_emb.embed_claim(t)) for _, t in items]
                    _mo = self._forge_manifold.update_manifold(_states, eta=None)
                    _base = _np.full(len(items), 1.0 / len(items))
                    _adj = _np.maximum(_base * (1.0 + _np.asarray(_mo["attractor_biases"])),
                                       0.5 * _base)
                    _adj = _adj / _adj.sum()
                    weights = {items[i][0]: float(_adj[i]) for i in range(len(items))}
                    self.last_synth_weights = {n: round(w, 4) for n, w in weights.items()}
            except Exception:
                weights = None

        if weights:
            items.sort(key=lambda it: -weights[it[0]])              # lead voice first
            base_budget = 1200
            parts = []
            for name, text in items:
                budget = int(base_budget * min(2.0, max(0.5, weights[name] * len(items))))
                parts.append(f"[your {name} lens — internal note]\n{text[:budget]}")
            combined = "\n\n".join(parts)
        else:
            combined = "\n\n".join(
                f"[your {name} lens — internal note]\n{text[:1200]}"
                for name, text in items
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
