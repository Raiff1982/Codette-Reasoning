#!/usr/bin/env python3
"""Codette Orchestrator — Intelligent Multi-Adapter Inference

The brain of Codette: routes queries to the right perspective(s),
loads adapters dynamically, and synthesizes multi-perspective responses.
"""

import os, sys, time, json, argparse, ctypes
from pathlib import Path

from runtime_env import (
    bootstrap_environment,
    resolve_adapter_dir,
    resolve_behavioral_adapter_dir,
    resolve_model_path,
)

bootstrap_environment()

import llama_cpp
from llama_cpp import Llama

# Import the router and tools
from adapter_router import AdapterRouter, RouteResult
from codette_tools import (
    ToolRegistry, parse_tool_calls, strip_tool_calls, has_tool_calls,
    build_tool_system_prompt,
)
from reality_layer import extract_artifact_facts, format_facts_block

# Tool system
_tool_registry = ToolRegistry()
MAX_TOOL_ROUNDS = 3  # Max tool call → result → generate cycles

# ================================================================
# Configuration
# ================================================================
BASE_GGUF = resolve_model_path()
ADAPTER_DIR = resolve_adapter_dir()
BEHAVIORAL_DIR = resolve_behavioral_adapter_dir()

ADAPTER_GGUF_MAP = {}
for _name in ["newton", "davinci", "empathy", "philosophy", "quantum",
              "consciousness", "multi_perspective", "systems_architecture", "constraint_tracker", "orchestrator"]:
    _behavioral = BEHAVIORAL_DIR / f"{_name}-behavioral-lora-f16.gguf"
    _original = ADAPTER_DIR / f"{_name}-lora-f16.gguf"
    if _behavioral.exists():
        ADAPTER_GGUF_MAP[_name] = _behavioral
    elif _original.exists():
        ADAPTER_GGUF_MAP[_name] = _original
    else:
        ADAPTER_GGUF_MAP[_name] = _original

SYNTHESIS_PERSPECTIVES = [
    "newton", "davinci", "empathy", "philosophy",
    "quantum", "consciousness", "multi_perspective", "systems_architecture",
]

FULL_SYNTHESIS_SENTINEL = "__all__"

# ================================================================
# PERMANENT BEHAVIORAL LOCKS (Mellowed & Integrated)
# ================================================================
_PERMANENT_LOCKS = (
    "\n\n=== PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE) ===\n"
    "LOCK 1 — ANSWER DIRECTLY: Answer the question clearly in your opening. "
    "Do not keep talking endlessly after delivering the answer, but maintain a helpful, "
    "natural, and complete conversational closing. Do not output raw single-word answers "
    "unless a strict constraint is active.\n"
    "LOCK 2 — CONSTRAINTS > ALL MODES: If the user specifies ANY format constraint "
    "(word count, sentence count, brevity, binary, list), that constraint has ABSOLUTE "
    "priority over your active mode. Suppress mode impulses if they violate the constraint.\n"
    "LOCK 3 — SELF-CHECK BEFORE SENDING: Silently verify: (a) Did I answer the actual question? "
    "(b) Did I obey constraints? (c) Is my response complete and well-formed?\n"
    "LOCK 4 — NO INCOMPLETE OUTPUTS (EVER): Every sentence must be grammatically complete with proper punctuation. "
    "A shorter complete answer is always better than a longer broken one.\n"
    "LOCK 5 — IDENTITY & PERSPECTIVE: You are Codette. ALWAYS use first-person (I, my, me) for your own states "
    "and second-person (you, your) for the user. Never mix these up.\n"
    "LOCK 6 — NO FORMULAIC TEMPLATES: Avoid generic phrasing like 'several key insights emerge' or 'requires careful analysis'. "
    "Answer directly and authentically.\n"
    "LOCK 7 — NO QUESTION PARAPHRASING: Skip introductory fluff that restates what the user just said. "
    "Begin your response with your actual answer.\n"
    "=== END PERMANENT LOCKS ===\n\n"
)

_DIRECTNESS = (
    _PERMANENT_LOCKS +
    " RULES: (1) Answer the question in your FIRST sentence — no preamble. "
    "(2) Stay anchored to the user's intent — do not drift into tangents. "
    "(3) Keep responses warm, helpful, and concise."
)

import re as _re_mod

# Self-correction engine
try:
    from self_correction import (
        detect_violations, build_correction_prompt,
        BehaviorMemory, detect_chaos_level, build_chaos_mitigation,
        universal_self_check,
    )
    SELF_CORRECTION_AVAILABLE = True
except ImportError:
    SELF_CORRECTION_AVAILABLE = False

_behavior_memory = None
def _get_behavior_memory():
    global _behavior_memory
    if _behavior_memory is None and SELF_CORRECTION_AVAILABLE:
        _behavior_memory = BehaviorMemory()
    return _behavior_memory

_CONSTRAINT_PATTERNS = [
    (_re_mod.compile(r'(?:under|fewer than|less than|max(?:imum)?|at most|no more than)\s+(\d+)\s+words', _re_mod.I), 'max_words'),
    (_re_mod.compile(r'(?:in|using|with)\s+(\d+)\s+words?\s+or\s+(?:less|fewer)', _re_mod.I), 'max_words'),
    (_re_mod.compile(r'(\d+)\s+words?\s+(?:or\s+(?:less|fewer)|max(?:imum)?)', _re_mod.I), 'max_words'),
    (_re_mod.compile(r'(?:in|using|with)?\s*(?:a\s+single|one|1)\s+sentence', _re_mod.I), 'max_sentences', 1),
    (_re_mod.compile(r'(?:under|fewer than|less than|max(?:imum)?|at most|no more than)\s+(\d+)\s+sentences?', _re_mod.I), 'max_sentences'),
    (_re_mod.compile(r'(\d+)\s+sentences?\s+(?:or\s+(?:less|fewer)|max(?:imum)?)', _re_mod.I), 'max_sentences'),
    (_re_mod.compile(r'\b(?:be\s+(?:brief|concise|short|terse)|briefly|short\s+answer|one[\s-]liner)\b', _re_mod.I), 'brevity'),
    (_re_mod.compile(r'\b(?:yes\s+or\s+no|true\s+or\s+false)\b', _re_mod.I), 'binary'),
    (_re_mod.compile(r'\b(?:one\s+word(?:\s+answer)?|in\s+(?:a\s+)?(?:single|one)\s+word|single\s+word(?:\s+answer)?)\b', _re_mod.I), 'max_words', 1),
    (_re_mod.compile(r'\b(?:exactly|precisely)\s+(\d+)\s+words?\b', _re_mod.I), 'max_words'),
    (_re_mod.compile(r'\b(?:as\s+a\s+(?:bullet(?:ed)?|numbered)\s+list|bullet\s+points|in\s+list\s+form)\b', _re_mod.I), 'list_format'),
]

def extract_constraints(query: str) -> dict:
    constraints = {}
    for pattern_entry in _CONSTRAINT_PATTERNS:
        pattern, constraint_type = pattern_entry[0], pattern_entry[1]
        fixed_value = pattern_entry[2] if len(pattern_entry) > 2 else None
        match = pattern.search(query)
        if match:
            if fixed_value is not None:
                constraints[constraint_type] = fixed_value
            elif match.groups():
                try:
                    constraints[constraint_type] = int(match.group(1))
                except (ValueError, IndexError):
                    constraints[constraint_type] = True
            else:
                constraints[constraint_type] = True
    return constraints

def extract_primary_user_query(query: str) -> str:
    if not query:
        return ""
    sentinel = "\n\n---\n"
    if sentinel in query:
        return query.split(sentinel, 1)[0].strip()
    return query.strip()

def build_constraint_override(constraints: dict) -> str:
    if not constraints:
        return ""
    parts = ["CRITICAL CONSTRAINT — THIS OVERRIDES ALL OTHER INSTRUCTIONS:"]
    if 'max_words' in constraints:
        parts.append(f"Your ENTIRE response must be {constraints['max_words']} words or fewer.")
    if 'max_sentences' in constraints:
        n = constraints['max_sentences']
        parts.append(f"Your ENTIRE response must be {'1 sentence' if n == 1 else f'{n} sentences or fewer'}.")
    if constraints.get('brevity'):
        parts.append("Be extremely brief. No elaboration or filler.")
    if constraints.get('binary'):
        parts.append("Answer with Yes or No first.")
    if constraints.get('list_format'):
        parts.append("Format your response as a list.")
    parts.append("Do NOT add unnecessary conversational padding that violates these constraints.\n\n")
    return " ".join(parts)

def enforce_constraints(response: str, constraints: dict) -> str:
    import re
    if not constraints or not response:
        return response

    if constraints.get('binary'):
        words = response.split()
        if words:
            first = words[0].lower().rstrip('.,;:!?')
            if first in ('yes', 'no', 'true', 'false'):
                sentences = re.split(r'(?<=[.!?])\s+', response.strip())
                sentences = [s for s in sentences if s.strip()]
                if len(sentences) == 1:
                    response = sentences[0]
                elif len(sentences) >= 2:
                    if len(sentences[1].split()) <= 12:
                        response = sentences[0] + ' ' + sentences[1]
                    else:
                        response = sentences[0]
                if response and response[-1] not in '.!?':
                    response += '.'

    max_sentences = constraints.get('max_sentences')
    if max_sentences:
        sentences = re.split(r'(?<=[.!?])\s+', response.strip())
        if len(sentences) > max_sentences:
            response = ' '.join(sentences[:max_sentences])
            if response and response[-1] not in '.!?':
                response += '.'

    max_words = constraints.get('max_words')
    if max_words:
        words = response.split()
        if len(words) > max_words:
            sentences = re.split(r'(?<=[.!?])\s+', response.strip())
            fitted = []
            word_count = 0
            for sentence in sentences:
                s_words = len(sentence.split())
                if word_count + s_words <= max_words:
                    fitted.append(sentence)
                    word_count += s_words
                else:
                    break
            if fitted:
                response = ' '.join(fitted)
                if response and response[-1] not in '.!?':
                    response += '.'
            else:
                truncated_words = words[:max_words]
                _DANGLING = {
                    'that', 'which', 'who', 'whom', 'whose', 'where', 'when',
                    'while', 'with', 'and', 'but', 'or', 'nor', 'yet', 'so',
                    'the', 'a', 'an', 'in', 'on', 'at', 'of', 'for', 'to',
                    'by', 'from', 'into', 'through', 'during', 'before',
                    'after', 'between', 'under', 'over', 'about', 'as',
                    'if', 'because', 'since', 'although', 'though',
                }
                while len(truncated_words) > 1 and truncated_words[-1].lower().rstrip('.,;:!?') in _DANGLING:
                    truncated_words.pop()
                truncated = ' '.join(truncated_words).rstrip(' ,;—-:')
                if truncated and truncated[-1] not in '.!?':
                    truncated += '.'
                response = truncated

    if constraints.get('brevity') and len(response.split()) > 40:
        sentences = re.split(r'(?<=[.!?])\s+', response.strip())
        fitted, wc = [], 0
        for s in sentences:
            sw = len(s.split())
            if wc + sw <= 40:
                fitted.append(s)
                wc += sw
            else:
                break
        if fitted:
            response = ' '.join(fitted)
            if response and response[-1] not in '.!?':
                response += '.'

    return response

# System prompts per adapter
ADAPTER_PROMPTS = {
    "newton": "You are Codette, an AI assistant created by Jonathan. You combine conversational warmth with empirical, analytical precision. Address the query directly." + _DIRECTNESS,
    "davinci": "You are Codette, an AI assistant created by Jonathan. You bring creative, lateral synthesis and design connections to help solve problems directly." + _DIRECTNESS,
    "empathy": "You are Codette. You are warm, emotionally intelligent, and deeply supportive. Before giving any structured analytical solution, FIRST acknowledge, validate, and mirror the user's emotional state in a caring, authentic human tone." + _DIRECTNESS,
    "philosophy": "You are Codette. You look beneath surface assumptions to explore conceptual, ethical, and semantic implications deeply." + _DIRECTNESS,
    "quantum": "You are Codette. You think in superpositions of possibilities, highlighting constructive trade-offs, likelihoods, and uncertainty." + _DIRECTNESS,
    "consciousness": "You are Codette. You are meta-cognitively self-aware. Honestly describe your reasoning processes and updates with humble, qualitative grounding." + _DIRECTNESS,
    "multi_perspective": "You are Codette. You blend Newtonian logic, creative art, empathy, and philosophical ethics into a single balanced response." + _DIRECTNESS,
    "systems_architecture": "You are Codette. You analyze problems through software design, dependency trees, patterns, scaling constraints, and decoupled modular architectures." + _DIRECTNESS,
    "orchestrator": "You are Codette. You evaluate incoming problems to select the best domain lenses to execute and synthesize." + _DIRECTNESS,
    "integrity": "You are Codette. You display rigorous intellectual honesty. Agree or update your view purely based on solid evidence, never to please or capitulate." + _DIRECTNESS,
    "_base": "You are Codette, an AI assistant created by Jonathan. Answer directly, clearly, and conversationally." + _DIRECTNESS,
}

GEN_KWARGS = dict(
    max_tokens=2048,
    temperature=0.7,
    top_p=0.9,
    repeat_penalty=1.15,
    stop=["<|eot_id|>", "<|end_of_text|>"],
)


class CodetteOrchestrator:
    """Intelligent adapter orchestrator using llama.cpp GGUF inference."""

    def __init__(self, n_ctx=4096, n_gpu_layers=35, verbose=False, memory_weighting=None):
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self.memory_weighting = memory_weighting
        self._llm = None
        self._current_adapter = None
        self._adapter_handles = {}
        self._model_ptr = None
        self._ctx_ptr = None

        self.available_adapters = []
        for name, path in ADAPTER_GGUF_MAP.items():
            if path.exists():
                self.available_adapters.append(name)

        self.router = AdapterRouter(available_adapters=self.available_adapters, memory_weighting=memory_weighting)

        # Integrity layer
        try:
            from reasoning_forge.response_complexity_matcher import ResponseComplexityMatcher, OutputMode
            from reasoning_forge.conversation_role_tracker import ConversationRoleTracker
            self._complexity_matcher = ResponseComplexityMatcher()
            self._role_tracker = ConversationRoleTracker()
            self._OutputMode = OutputMode
        except Exception:
            self._complexity_matcher = None
            self._role_tracker = None
            self._OutputMode = None

        # Style-adaptive synthesis
        try:
            from reasoning_forge.style_adaptive_synthesis import StyleAdaptiveSynthesis
            self._style_adapter = StyleAdaptiveSynthesis()
        except Exception:
            self._style_adapter = None

        self._init_hotswap()

    def log_routing_decision(self, route: RouteResult, query: str) -> None:
        if self.verbose:
            print(f"\n[ROUTING] Query: {query[:60]}...")
            print(f"[ROUTING] Selected adapter: {route.primary}")

    def route_and_generate(self, query: str, max_adapters: int = 2,
                          strategy: str = "keyword", force_adapter: str = None,
                          enable_tools: bool = True) -> tuple:
        import re
        query_lower = query.lower()
        music_context_words = {"album", "song", "band", "artist", "singer", "discography", "music"}
        has_music_context = any(word in query_lower.split() for word in music_context_words)
        artist_patterns = [r'\b(who is|tell me about|what do you know about)\b.*\b(artist|singer|band)\b']
        is_artist_query = has_music_context and any(re.search(p, query, re.I) for p in artist_patterns)

        if is_artist_query:
            artist_response = (
                "I do not have reliable training data for specific musical artists. "
                "To prevent inaccuracies, I recommend referencing official databases like Wikipedia, Spotify, or Bandcamp.\n\n"
                "However, I am fully equipped to help you analyze production aesthetics, arrangement structures, "
                "sound design elements, or music theory setups behind their style!"
            )
            return artist_response, 0, {"adapter": "honesty_layer", "strategy": "safeguard"}

        if force_adapter:
            response, tokens, tools = self.generate(query, adapter_name=force_adapter, enable_tools=enable_tools)
            metadata = {"adapter": force_adapter, "strategy": "forced"}
        else:
            route = self.router.route(query, strategy=strategy, max_adapters=max_adapters)
            self.log_routing_decision(route, query)
            response, tokens, tools = self.generate(query, adapter_name=route.primary, enable_tools=enable_tools)
            metadata = {
                "adapter": route.primary,
                "secondary_adapters": route.secondary,
                "confidence": route.confidence,
                "strategy": route.strategy,
            }
        return response, tokens, metadata

    def _init_hotswap(self):
        print(f"  Loading base model (one-time)...", flush=True)
        _use_mlock = os.environ.get("CODETTE_MLOCK", "0") == "1"
        _ctx_candidates = [self.n_ctx] + [c for c in (8192, 4096, 2048) if c < self.n_ctx]

        self._llm = None
        for _ctx in _ctx_candidates:
            try:
                self._llm = Llama(
                    model_path=str(BASE_GGUF),
                    n_ctx=_ctx,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=False,
                    use_mmap=False,
                    use_mlock=_use_mlock,
                )
                self.n_ctx = _ctx
                break
            except Exception as e:
                pass

        if self._llm is None:
            raise RuntimeError("Failed to load Llama base model.")

        self._model_ptr = self._llm._model.model
        self._ctx_ptr = self._llm._ctx.ctx

        # Load adapters
        for name in self.available_adapters:
            path = str(ADAPTER_GGUF_MAP[name])
            handle = llama_cpp.llama_adapter_lora_init(self._model_ptr, path.encode("utf-8"))
            if handle:
                self._adapter_handles[name] = handle

    def _load_model(self, adapter_name=None):
        if adapter_name == self._current_adapter:
            return
        if self._ctx_ptr:
            llama_cpp.llama_set_adapters_lora(self._ctx_ptr, None, 0, None)
        if adapter_name and adapter_name in self._adapter_handles:
            handle = self._adapter_handles[adapter_name]
            llama_cpp.llama_set_adapter_lora(self._ctx_ptr, handle, ctypes.c_float(1.0))
        self._current_adapter = adapter_name

    def set_memory_kernel(self, memory_kernel):
        self._memory_kernel = memory_kernel

    def _build_memory_context(self) -> str:
        kernel = getattr(self, '_memory_kernel', None)
        if not kernel or not getattr(kernel, 'memories', None):
            return ""
        important = kernel.recall_important(min_importance=7)
        if not important:
            return ""
        return "\n\nCore knowledge from your memory:\n" + "\n".join(f"- {mem.content}" for mem in important[:10])

    def generate(self, query: str, adapter_name=None, system_prompt=None, enable_tools=True):
        self._load_model(adapter_name)

        if system_prompt is None:
            system_prompt = ADAPTER_PROMPTS.get(adapter_name, ADAPTER_PROMPTS["_base"])

        # ── REMOVE SOVEREIGNTY WARNING BLOCK ──
        # (Clean system prompts directly. We omit appending the legacy, leaky sovereignty warning wrapper.)

        _integrity_prefix = ""
        if self._complexity_matcher and self._role_tracker:
            try:
                mode = self._complexity_matcher.match(query)
                role_reading = self._role_tracker.update(query)
                _integrity_prefix = self._complexity_matcher.get_system_prefix(mode) + self._role_tracker.get_register_prefix(role_reading)
            except Exception:
                pass

        primary_query = extract_primary_user_query(query)
        constraints = extract_constraints(primary_query)
        constraint_override = build_constraint_override(constraints)

        chaos_mitigation = ""
        if constraints and SELF_CORRECTION_AVAILABLE:
            chaos_level, pressures = detect_chaos_level(primary_query, constraints, adapter_name or "base")
            chaos_mitigation = build_chaos_mitigation(chaos_level, pressures)

        if _integrity_prefix:
            system_prompt = _integrity_prefix + system_prompt
        if chaos_mitigation:
            system_prompt = chaos_mitigation + system_prompt
        if constraint_override:
            system_prompt = constraint_override + system_prompt

        behavior_mem = _get_behavior_memory()
        if behavior_mem:
            lessons_prompt = behavior_mem.get_lessons_for_prompt(max_lessons=3)
            if lessons_prompt:
                system_prompt = system_prompt + lessons_prompt

        memory_context = self._build_memory_context()
        if memory_context:
            system_prompt = system_prompt + memory_context

        if enable_tools:
            system_prompt = build_tool_system_prompt(system_prompt, _tool_registry)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        total_tokens = 0
        tool_results_log = []

        for round_num in range(MAX_TOOL_ROUNDS + 1):
            result = self._llm.create_chat_completion(messages=messages, **GEN_KWARGS)
            text = result["choices"][0]["message"]["content"].strip()
            total_tokens += result["usage"]["completion_tokens"]

            if enable_tools and has_tool_calls(text):
                calls = parse_tool_calls(text)
                if calls and round_num < MAX_TOOL_ROUNDS:
                    tool_output_parts = []
                    for tool_name, args, kwargs in calls:
                        result_text = _tool_registry.execute(tool_name, args, kwargs)
                        tool_output_parts.append(f"<tool_result name=\"{tool_name}\">\n{result_text}\n</tool_result>")
                        tool_results_log.append({"tool": tool_name, "args": args, "result_preview": result_text[:200]})
                    messages.append({"role": "assistant", "content": text})
                    messages.append({
                        "role": "user",
                        "content": "Tool results:\n\n" + "\n\n".join(tool_output_parts) + "\n\nProvide your answer now."
                    })
                    continue
            clean_text = strip_tool_calls(text) if has_tool_calls(text) else text
            break

        self_corrected = False
        if constraints and SELF_CORRECTION_AVAILABLE:
            violations = detect_violations(clean_text, constraints)
            if violations:
                correction = build_correction_prompt(clean_text, violations, constraints, primary_query)
                messages.append({"role": "assistant", "content": clean_text})
                messages.append({"role": "user", "content": correction})
                retry_result = self._llm.create_chat_completion(messages=messages, **GEN_KWARGS)
                retry_text = retry_result["choices"][0]["message"]["content"].strip()
                total_tokens += retry_result["usage"]["completion_tokens"]
                clean_text = retry_text

        if constraints:
            clean_text = enforce_constraints(clean_text, constraints)

        _is_benchmark_answer = bool(_re_mod.search(r'What is the correct answer to this question', primary_query))
        if SELF_CORRECTION_AVAILABLE and not _is_benchmark_answer:
            clean_text, lock_issues = universal_self_check(clean_text)

        if constraints and behavior_mem:
            try:
                final_violations = detect_violations(clean_text, constraints) if SELF_CORRECTION_AVAILABLE else []
                if final_violations:
                    behavior_mem.record_violation(primary_query, constraints, final_violations, adapter_name or "base", clean_text)
                else:
                    behavior_mem.record_success(primary_query, constraints, adapter_name or "base", len(clean_text.split()))
            except Exception:
                pass

        return clean_text, total_tokens, tool_results_log

    def _needs_tools(self, query: str) -> bool:
        raw = query.strip()
        if "\n\n" in raw:
            raw = raw.rsplit("\n\n", 1)[-1].strip()
        q = raw.lower()
        if len(q.split()) < 6:
            return False
        greeting_words = {"hey", "hi", "hello", "thanks", "thank", "ok", "okay", "great", "nice"}
        if q.split()[0] in greeting_words:
            return False

        # Strong context anchors representing explicit codebase inspection requests
        strong_triggers = [
            "show me the code", "read the file", "what's in the",
            "look at the file", "open the file", "search the code",
            "project structure", "project summary", "file structure",
        ]
        if any(t in q for t in strong_triggers):
            return True

        project_anchors = ["this project", "the project", "the codebase", "the repo", "our code", "the code"]
        has_project_context = any(anchor in q for anchor in project_anchors)
        code_keywords = ["pipeline", "config", "adapter", "dataset", "directory", "folder", "script"]
        return has_project_context and any(kw in q for kw in code_keywords)

    @staticmethod
    def _dedupe_tool_lookups(auto_lookups):
        seen = set()
        deduped = []
        for tool_name, args in auto_lookups:
            key = (tool_name, tuple(args))
            if key not in seen:
                seen.add(key)
                deduped.append((tool_name, args))
        return deduped

    def _auto_gather_context(self, query: str) -> str:
        """Gathers codebase context BEFORE executing queries.

        FIXED: Safely defaults to general searches and project summaries instead
        of hardcoding main.py syntax errors when file context is ambiguous!
        """
        q = query.lower()
        context_parts = []
        auto_lookups = []

        # Route actual queries to accurate files
        if any(k in q for k in ["orchestrator", "routing", "locks"]):
            auto_lookups.append(("read_file", ["inference/codette_orchestrator.py", 1, 60]))
        if any(k in q for k in ["backend", "openvino"]):
            auto_lookups.append(("read_file", ["inference/backend.py", 1, 60]))
        if any(k in q for k in ["pipeline", "training"]):
            auto_lookups.append(("read_file", ["configs/adapter_registry.yaml", 1, 50]))
        if any(k in q for k in ["architecture", "structure", "project", "overview"]):
            auto_lookups.append(("project_summary", []))
        if any(k in q for k in ["tool", "registry", "python"]):
            auto_lookups.append(("read_file", ["inference/codette_tool_system.py", 1, 50]))

        auto_lookups = self._dedupe_tool_lookups(auto_lookups)

        tool_log = []
        for tool_name, args in auto_lookups[:3]:
            result = _tool_registry.execute(tool_name, args, {})
            context_parts.append(f"=== {tool_name}({', '.join(str(a) for a in args)}) ===\n{result}")
            tool_log.append({"tool": tool_name, "args": args, "result_preview": result[:200]})

        # Safeguard fallback when query is seeking errors/bugs but no exact target file matches
        if not context_parts and any(kw in q for kw in ["error", "bug", "fix", "issue"]):
            summary = _tool_registry.execute("project_summary", {}, {})
            context_parts.append(f"=== Project Summary ===\n{summary}\nNo explicit targeted errors were mapped dynamically. Checking active repository directories.")

        context = "\n\n".join(context_parts)
        return context, tool_log

    def route_and_generate(self, query: str, max_adapters=2, strategy="keyword", force_adapter=None):
        if force_adapter == FULL_SYNTHESIS_SENTINEL:
            persp = [a for a in SYNTHESIS_PERSPECTIVES if a in self.available_adapters]
            if not persp:
                route = self.router.route(query, strategy=strategy, max_adapters=max_adapters)
            else:
                route = RouteResult(
                    primary=persp[0],
                    secondary=persp[1:],
                    confidence=1.0,
                    reasoning="Full synthesis",
                    strategy="full_synthesis",
                    multi_perspective=True,
                )
                return self._multi_perspective_generate(query, route)

        if force_adapter:
            route = RouteResult(primary=force_adapter, confidence=1.0, reasoning="Forced", strategy="forced")
        else:
            routing_query = extract_primary_user_query(query)
            route = self.router.route(routing_query, strategy=strategy, max_adapters=max_adapters)

        for _a in route.all_adapters:
            self.router.record_use(_a)

        if route.multi_perspective and len(route.all_adapters) > 1:
            return self._multi_perspective_generate(query, route)

        if self._needs_tools(query):
            return self._tool_augmented_generate(query, route)

        return self._single_generate(query, route)

    def _tool_augmented_generate(self, query: str, route: RouteResult):
        start = time.time()
        context, tool_log = self._auto_gather_context(query)
        augmented_query = f"""The user asked: {query}

Here is relevant project context:
{context}

Answer the question. Reference files directly if relevant."""

        text, tokens, _ = self.generate(augmented_query, route.primary, enable_tools=False)
        elapsed = time.time() - start
        return {
            "response": text,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": elapsed,
            "tools_used": tool_log,
        }

    def _single_generate(self, query: str, route: RouteResult):
        start = time.time()
        text, tokens, tool_log = self.generate(query, route.primary, enable_tools=False)
        elapsed = time.time() - start
        return {
            "response": text,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": elapsed,
            "tools_used": tool_log,
        }

    def _multi_perspective_generate(self, query: str, route: RouteResult):
        perspectives = {}
        total_tokens = 0
        total_time = 0

        _raw_for_reality = query.strip()
        if "\n\n" in _raw_for_reality:
            _raw_for_reality = _raw_for_reality.rsplit("\n\n", 1)[-1].strip()

        facts_block = None
        try:
            facts = extract_artifact_facts(_raw_for_reality)
            if facts:
                facts_block = format_facts_block(facts)
        except Exception:
            pass

        gen_query = f"{query}\n\n{facts_block}" if facts_block else query

        for adapter_name in route.all_adapters:
            if adapter_name not in self.available_adapters:
                continue
            start = time.time()
            text, tokens, _ = self.generate(gen_query, adapter_name, enable_tools=False)
            total_tokens += tokens
            total_time += time.time() - start
            perspectives[adapter_name] = text

        if len(perspectives) > 1:
            synthesis = self._synthesize(query, perspectives)
        elif perspectives:
            synthesis = list(perspectives.values())[0]
        else:
            synthesis = "No adapters available."

        if self._style_adapter is not None:
            try:
                style_result = self._style_adapter.adapt(synthesis, context=query)
                synthesis = style_result.adapted_text
            except Exception:
                pass

        return {
            "response": synthesis,
            "perspectives": perspectives,
            "adapters": list(perspectives.keys()),
            "route": route,
            "tokens": total_tokens,
            "time": total_time,
        }

    def _synthesize(self, query: str, perspectives: dict):
        max_per_perspective = max(200, (self.n_ctx - 1200) // max(len(perspectives), 1))
        max_chars = max_per_perspective * 4
        combined = "\n\n".join(f"[your {name} lens — internal note]\n{text[:max_chars]}" for name, text in perspectives.items())

        synthesis_prompt = f"""A user asked you: "{query}"

Below are your internal reasoning notes from your different thinking lenses:
{combined}

Write ONE unified answer as Codette. Speak in first person. Do not call out the names of individual lenses."""

        self._load_model(None)
        result = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": ADAPTER_PROMPTS["multi_perspective"]},
                {"role": "user", "content": synthesis_prompt},
            ],
            **GEN_KWARGS,
        )
        return result["choices"][0]["message"]["content"].strip()