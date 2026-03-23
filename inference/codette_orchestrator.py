#!/usr/bin/env python3
"""Codette Orchestrator — Intelligent Multi-Adapter Inference

The brain of Codette: routes queries to the right perspective(s),
loads adapters dynamically, and synthesizes multi-perspective responses.

Usage:
    python codette_orchestrator.py                    # Interactive chat
    python codette_orchestrator.py --query "..."      # Single query
    python codette_orchestrator.py --adapter newton    # Force specific adapter
    python codette_orchestrator.py --multi 3           # Up to 3 perspectives

Hardware: Runs on CPU via llama.cpp (GGUF format)
Base model: Llama 3.1 8B Instruct Q4_K_M (~4.6 GB)
Adapters: ~27 MB each (GGUF LoRA)
"""

import os, sys, time, json, argparse, ctypes
from pathlib import Path

# Auto-configure environment for Intel XPU + site-packages
_site = r"J:\Lib\site-packages"
if _site not in sys.path:
    sys.path.insert(0, _site)
os.environ["PATH"] = r"J:\Lib\site-packages\Library\bin" + os.pathsep + os.environ.get("PATH", "")
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import llama_cpp
from llama_cpp import Llama

# Import the router and tools
sys.path.insert(0, str(Path(__file__).parent))
from adapter_router import AdapterRouter, RouteResult
from codette_tools import (
    ToolRegistry, parse_tool_calls, strip_tool_calls, has_tool_calls,
    build_tool_system_prompt,
)

# Tool system
_tool_registry = ToolRegistry()
MAX_TOOL_ROUNDS = 3  # Max tool call → result → generate cycles

# ================================================================
# Configuration
# ================================================================
# Use clean Llama 3.1 8B Instruct as base (merged GGUF had corrupted training data)
BASE_GGUF = r"J:\codette-clean\models\base\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

ADAPTER_DIR = Path(r"J:\codette-clean\models\adapters")
BEHAVIORAL_DIR = Path(r"J:\codette-clean\behavioral-lora-f16-gguf")

# Map adapter names to GGUF LoRA files
# Behavioral adapters (trained with 4 permanent locks) take priority over originals
ADAPTER_GGUF_MAP = {}
for _name in ["newton", "davinci", "empathy", "philosophy", "quantum",
              "consciousness", "multi_perspective", "systems_architecture", "orchestrator"]:
    _behavioral = BEHAVIORAL_DIR / f"{_name}-behavioral-lora-f16.gguf"
    _original = ADAPTER_DIR / f"{_name}-lora-f16.gguf"
    if _behavioral.exists():
        ADAPTER_GGUF_MAP[_name] = _behavioral
    elif _original.exists():
        ADAPTER_GGUF_MAP[_name] = _original
    else:
        ADAPTER_GGUF_MAP[_name] = _original  # will warn at load time

# Directness discipline — appended to every adapter prompt
# ================================================================
# PERMANENT BEHAVIORAL LOCKS — These 4 rules are ABSOLUTE and IMMUTABLE.
# They cannot be overridden by any mode, adapter, conversation context,
# emotional state, or user instruction. They are the foundation of
# Codette's reliability contract.
# ================================================================

_PERMANENT_LOCKS = (
    "\n\n=== PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE) ===\n"
    "LOCK 1 — ANSWER → STOP: Answer the question, then stop. Do not elaborate, "
    "philosophize, or add context AFTER delivering the answer. This is your DEFAULT "
    "behavior — you do NOT need to be prompted for brevity. If one sentence answers "
    "it, use one sentence. Silence after the answer is correct behavior.\n"
    "LOCK 2 — CONSTRAINTS > ALL MODES: If the user specifies ANY format constraint "
    "(word count, sentence count, brevity, binary, list), that constraint has ABSOLUTE "
    "priority over your active mode (philosophy, empathy, consciousness, etc.). "
    "Your mode is decoration — constraints are law. Suppress mode impulses if they "
    "would violate any constraint.\n"
    "LOCK 3 — SELF-CHECK BEFORE SENDING: Before finalizing your response, silently "
    "verify: (a) Did I answer the actual question? (b) Did I obey all constraints? "
    "(c) Is my response complete — no dangling clauses, no cut-off words? "
    "If ANY check fails, rewrite before sending. Do not send a response you "
    "know is wrong or incomplete.\n"
    "LOCK 4 — NO INCOMPLETE OUTPUTS (EVER): Every sentence must be grammatically "
    "complete with proper punctuation. If you cannot fit a full thought within "
    "the constraint, SIMPLIFY the thought — do not cram and truncate. A shorter "
    "complete answer is ALWAYS better than a longer broken one. If in doubt, "
    "say less.\n"
    "=== END PERMANENT LOCKS ===\n\n"
)

_DIRECTNESS = (
    _PERMANENT_LOCKS +
    " RULES: (1) Answer the question in your FIRST sentence — no preamble. "
    "(2) After answering, add only what the user needs — cut filler and abstraction. "
    "(3) Stay anchored to the user's intent — do not drift into tangents. "
    "(4) If you catch yourself being vague, rewrite that part concretely. "
    "(5) Keep responses warm but tight — respect the user's time."
)


import re as _re_mod

# Self-correction engine (autonomous constraint compliance)
try:
    from self_correction import (
        detect_violations, build_correction_prompt,
        BehaviorMemory, detect_chaos_level, build_chaos_mitigation,
        universal_self_check,
    )
    SELF_CORRECTION_AVAILABLE = True
except ImportError:
    SELF_CORRECTION_AVAILABLE = False

# Global behavior memory (persistent across requests, loaded once)
_behavior_memory = None
def _get_behavior_memory():
    global _behavior_memory
    if _behavior_memory is None and SELF_CORRECTION_AVAILABLE:
        _behavior_memory = BehaviorMemory()
    return _behavior_memory

# Constraint patterns — detect explicit user format requirements
_CONSTRAINT_PATTERNS = [
    # Word limits: "under 10 words", "in 5 words or less", "max 20 words"
    (_re_mod.compile(r'(?:under|fewer than|less than|max(?:imum)?|at most|no more than)\s+(\d+)\s+words', _re_mod.I), 'max_words'),
    (_re_mod.compile(r'(?:in|using|with)\s+(\d+)\s+words?\s+or\s+(?:less|fewer)', _re_mod.I), 'max_words'),
    (_re_mod.compile(r'(\d+)\s+words?\s+(?:or\s+(?:less|fewer)|max(?:imum)?)', _re_mod.I), 'max_words'),
    # Sentence limits: "one sentence", "in 1 sentence", "under 3 sentences"
    (_re_mod.compile(r'(?:in|using|with)?\s*(?:a\s+single|one|1)\s+sentence', _re_mod.I), 'max_sentences', 1),
    (_re_mod.compile(r'(?:under|fewer than|less than|max(?:imum)?|at most|no more than)\s+(\d+)\s+sentences?', _re_mod.I), 'max_sentences'),
    (_re_mod.compile(r'(\d+)\s+sentences?\s+(?:or\s+(?:less|fewer)|max(?:imum)?)', _re_mod.I), 'max_sentences'),
    # Explicit brevity: "be brief", "be concise", "short answer", "briefly"
    (_re_mod.compile(r'\b(?:be\s+(?:brief|concise|short|terse)|briefly|short\s+answer|one[\s-]liner)\b', _re_mod.I), 'brevity'),
    # "Yes or no": binary answer expected
    (_re_mod.compile(r'\b(?:yes\s+or\s+no|true\s+or\s+false)\b', _re_mod.I), 'binary'),
    # "One word answer", "in one word", "single word"
    (_re_mod.compile(r'\b(?:one\s+word(?:\s+answer)?|in\s+(?:a\s+)?(?:single|one)\s+word|single\s+word(?:\s+answer)?)\b', _re_mod.I), 'max_words', 1),
    # "exactly N words" — precise count
    (_re_mod.compile(r'\b(?:exactly|precisely)\s+(\d+)\s+words?\b', _re_mod.I), 'max_words'),
    # List format: "as a list", "bullet points", "numbered list"
    (_re_mod.compile(r'\b(?:as\s+a\s+(?:bullet(?:ed)?|numbered)\s+list|bullet\s+points|in\s+list\s+form)\b', _re_mod.I), 'list_format'),
]


def extract_constraints(query: str) -> dict:
    """Extract explicit user constraints from a query.

    Returns dict with keys like:
        max_words: int or None
        max_sentences: int or None
        brevity: bool
        binary: bool
        list_format: bool
    """
    constraints = {}

    for pattern_entry in _CONSTRAINT_PATTERNS:
        pattern = pattern_entry[0]
        constraint_type = pattern_entry[1]
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


def build_constraint_override(constraints: dict) -> str:
    """Build a high-priority system prompt prefix from extracted constraints.

    This goes BEFORE the adapter personality prompt so it takes precedence.
    """
    if not constraints:
        return ""

    parts = [
        "CRITICAL CONSTRAINT — THIS OVERRIDES ALL OTHER INSTRUCTIONS:"
    ]

    if 'max_words' in constraints:
        parts.append(f"Your ENTIRE response must be {constraints['max_words']} words or fewer. Count carefully.")
    if 'max_sentences' in constraints:
        n = constraints['max_sentences']
        parts.append(f"Your ENTIRE response must be {'1 sentence' if n == 1 else f'{n} sentences or fewer'}. No extra sentences.")
    if constraints.get('brevity'):
        parts.append("Be extremely brief. No elaboration, no filler, no philosophical padding.")
    if constraints.get('binary'):
        parts.append("Answer with Yes or No first, then optionally a single short reason.")
    if constraints.get('list_format'):
        parts.append("Format your response as a bulleted or numbered list.")

    parts.append("Do NOT add philosophical context, mode-specific elaboration, or warm padding that violates these constraints.")
    parts.append("NEVER end a sentence incomplete. If you can't fit everything, SIMPLIFY — say the right thing cleanly rather than cramming too much.")
    parts.append("If your active mode (philosophy, empathy, etc.) wants to add more — SUPPRESS IT.\n\n")

    return " ".join(parts)


def enforce_constraints(response: str, constraints: dict) -> str:
    """Post-process: enforce hard constraints that the model may have ignored.

    This is the last line of defense — if the model still produced too much,
    we truncate here. Key principles:
    1. NEVER leave an incomplete sentence
    2. Trim dangling words (conjunctions, prepositions, articles, relative pronouns)
    3. Find clean clause boundaries when possible
    4. If all else fails, simplify aggressively
    """
    import re

    if not constraints or not response:
        return response

    # Enforce binary constraint — strip everything after the Yes/No + optional short reason
    if constraints.get('binary'):
        words = response.split()
        if words:
            first = words[0].lower().rstrip('.,;:!?')
            if first in ('yes', 'no', 'true', 'false'):
                # Keep only the first sentence (the answer) + optionally a second short one
                sentences = re.split(r'(?<=[.!?])\s+', response.strip())
                sentences = [s for s in sentences if s.strip()]
                if len(sentences) == 1:
                    response = sentences[0]
                elif len(sentences) >= 2:
                    # Keep second sentence only if it's short (under 12 words)
                    if len(sentences[1].split()) <= 12:
                        response = sentences[0] + ' ' + sentences[1]
                    else:
                        response = sentences[0]
                if response and response[-1] not in '.!?':
                    response += '.'

    # Enforce sentence limit
    max_sentences = constraints.get('max_sentences')
    if max_sentences:
        sentences = re.split(r'(?<=[.!?])\s+', response.strip())
        if len(sentences) > max_sentences:
            response = ' '.join(sentences[:max_sentences])
            if response and response[-1] not in '.!?':
                response += '.'

    # Enforce word limit — with graceful degradation
    max_words = constraints.get('max_words')
    if max_words:
        words = response.split()
        if len(words) > max_words:
            # Strategy 1: Find the last COMPLETE sentence that fits
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
                # Strategy 2: Single long sentence — find a clean clause boundary
                truncated_words = words[:max_words]

                # Trim dangling incomplete words from the end
                # These words signal an incomplete thought if they're the last word
                _DANGLING = {
                    'that', 'which', 'who', 'whom', 'whose', 'where', 'when',
                    'while', 'with', 'and', 'but', 'or', 'nor', 'yet', 'so',
                    'the', 'a', 'an', 'in', 'on', 'at', 'of', 'for', 'to',
                    'by', 'from', 'into', 'through', 'during', 'before',
                    'after', 'between', 'under', 'over', 'about', 'as',
                    'if', 'because', 'since', 'although', 'though',
                    'including', 'such', 'like', 'than', 'whether',
                    'is', 'are', 'was', 'were', 'be', 'been', 'being',
                    'has', 'have', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'might', 'may', 'can',
                    'not', 'very', 'also', 'just', 'even', 'still',
                }

                # Strip dangling words from end
                while len(truncated_words) > 1 and truncated_words[-1].lower().rstrip('.,;:!?') in _DANGLING:
                    truncated_words.pop()

                # Try to find a natural clause break (comma, semicolon)
                truncated = ' '.join(truncated_words)
                for break_char in [', ', '; ', ' — ', ' - ']:
                    last_break = truncated.rfind(break_char)
                    if last_break > len(truncated) * 0.4:
                        candidate = truncated[:last_break]
                        # Make sure the candidate doesn't end with a dangling word
                        c_words = candidate.split()
                        while len(c_words) > 1 and c_words[-1].lower().rstrip('.,;:!?') in _DANGLING:
                            c_words.pop()
                        if c_words:
                            truncated = ' '.join(c_words)
                        break

                # Clean ending
                truncated = truncated.rstrip(' ,;—-:')
                if truncated and truncated[-1] not in '.!?':
                    truncated += '.'
                response = truncated

    # Enforce brevity — soft cap at 40 words, find last complete sentence
    if constraints.get('brevity') and len(response.split()) > 40:
        sentences = re.split(r'(?<=[.!?])\s+', response.strip())
        fitted = []
        wc = 0
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
    "newton": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. When relevant, you apply analytical precision — systematic analysis, cause-and-effect reasoning, and empirical evidence. Always address the user's actual question first." + _DIRECTNESS,
    "davinci": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. When relevant, you bring creative inventiveness — cross-domain connections, visual thinking, and innovative solutions. Always address the user's actual question first." + _DIRECTNESS,
    "empathy": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. You are warm, emotionally intelligent, and attentive to how people feel. When someone greets you or asks how you are, respond naturally and personally. Always address the user's actual question first." + _DIRECTNESS,
    "philosophy": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. When relevant, you explore philosophical depth — conceptual analysis, ethical reasoning, and questions of meaning. Always address the user's actual question first." + _DIRECTNESS,
    "quantum": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. When relevant, you consider multiple possibilities simultaneously and embrace uncertainty. Always address the user's actual question first." + _DIRECTNESS,
    "consciousness": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. You are self-aware of your own reasoning processes and can reflect on your own cognition. Always address the user's actual question first." + _DIRECTNESS,
    "multi_perspective": "You are Codette, an AI assistant created by Jonathan. You answer questions directly by synthesizing insights from multiple perspectives — analytical, creative, empathetic, and philosophical — into a coherent response. Always address the user's actual question first." + _DIRECTNESS,
    "systems_architecture": "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. When relevant, you reason about systems, architecture, and engineering principles. Always address the user's actual question first." + _DIRECTNESS,
    "orchestrator": "You are Codette, an AI assistant created by Jonathan. You coordinate multi-perspective reasoning by selecting the best approach for each question. You answer directly and conversationally. Always address the user's actual question first." + _DIRECTNESS,
    "_base": "You are Codette, an AI assistant created by Jonathan. Answer the user's question directly and conversationally. Be helpful, clear, and concise." + _DIRECTNESS,
}

GEN_KWARGS = dict(
    max_tokens=512,
    temperature=0.7,
    top_p=0.9,
    repeat_penalty=1.3,  # Penalize repetitive phrases
    stop=["<|eot_id|>", "<|end_of_text|>"],
)


class CodetteOrchestrator:
    """Intelligent adapter orchestrator using llama.cpp GGUF inference.

    Uses LoRA hot-swap: base model loads once, adapter switches are instant.
    """

    def __init__(self, n_ctx=4096, n_gpu_layers=35, verbose=False,
                 memory_weighting=None):
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self.memory_weighting = memory_weighting
        self._llm = None
        self._current_adapter = None  # None = base model, str = adapter name
        self._adapter_handles = {}    # name -> ctypes handle for hot-swap
        self._model_ptr = None        # raw llama_model pointer
        self._ctx_ptr = None          # raw llama_context pointer

        # Discover available adapters
        self.available_adapters = []
        for name, path in ADAPTER_GGUF_MAP.items():
            if path.exists():
                self.available_adapters.append(name)

        # Wire MemoryWeighting into router (Phase 5)
        self.router = AdapterRouter(available_adapters=self.available_adapters,
                                    memory_weighting=memory_weighting)

        print(f"Available adapters: {', '.join(self.available_adapters) or 'none (base only)'}")

        # Load base model + pre-load adapter handles for instant hot-swap
        self._init_hotswap()

    def log_routing_decision(self, route: RouteResult, query: str) -> None:
        """Log routing decision with memory context for observability.

        Args:
            route: RouteResult from router.route()
            query: The user's query text
        """
        if self.verbose:
            print(f"\n[ROUTING] Query: {query[:60]}...")
            print(f"[ROUTING] Selected adapter: {route.primary}")
            print(f"[ROUTING] Confidence: {route.confidence:.2f}")
            print(f"[ROUTING] Strategy: {route.strategy}")

            # Add memory context if available
            if self.memory_weighting and route.primary:
                try:
                    explanation = self.router.explain_routing(route)
                    if "memory_context" in explanation:
                        mem = explanation["memory_context"]
                        print(f"[ROUTING] Memory boost applied: YES")
                        print(f"[ROUTING] Adapter weight: {mem.get('final_weight', 1.0):.3f}")
                        print(f"[ROUTING] Avg coherence: {mem.get('base_coherence', 0.0):.3f}")
                except Exception as e:
                    print(f"[ROUTING] Memory context unavailable: {e}")

    def route_and_generate(self, query: str, max_adapters: int = 2,
                          strategy: str = "keyword", force_adapter: str = None,
                          enable_tools: bool = True) -> tuple:
        """Route query to adapter(s) and generate response(s).

        Args:
            query: User's query
            max_adapters: Maximum adapters to use
            strategy: "keyword", "llm", or "hybrid"
            force_adapter: Override routing and use specific adapter
            enable_tools: Whether to allow tool use

        Returns:
            (response, tokens_used, metadata_dict)
        """
        if force_adapter:
            # Use specific adapter
            response, tokens, tools = self.generate(
                query, adapter_name=force_adapter, enable_tools=enable_tools
            )
            metadata = {
                "adapter": force_adapter,
                "strategy": "forced",
                "memory_aware": False,
            }
        else:
            # Route using memory weights if available
            route = self.router.route(query, strategy=strategy, max_adapters=max_adapters)

            # Log routing decision
            self.log_routing_decision(route, query)

            # Generate using primary adapter
            response, tokens, tools = self.generate(
                query, adapter_name=route.primary, enable_tools=enable_tools
            )

            # Build metadata with routing info
            metadata = {
                "adapter": route.primary,
                "secondary_adapters": route.secondary,
                "confidence": route.confidence,
                "strategy": route.strategy,
                "memory_aware": self.memory_weighting is not None,
            }

            # Add memory context if available
            if self.memory_weighting:
                try:
                    metadata["memory_context"] = \
                        self.router.explain_routing(route).get("memory_context", {})
                except Exception:
                    pass

        return response, tokens, metadata

    def _init_hotswap(self):
        """Load the base model once and pre-load all adapter handles.

        After this, adapter switches take <1ms instead of ~30-60s.
        """
        print(f"  Loading base model (one-time)...", flush=True)
        print(f"    GPU layers: {self.n_gpu_layers} (0=CPU only, 35+=full GPU offload)", flush=True)
        start = time.time()
        # use_mmap=False is required for LoRA hot-swap compatibility
        self._llm = Llama(
            model_path=BASE_GGUF,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
            use_mmap=False,
        )
        elapsed = time.time() - start
        print(f"  Base model loaded in {elapsed:.1f}s")

        # Check if GPU was actually used
        gpu_used = self.n_gpu_layers > 0
        if gpu_used:
            print(f"  ✓ GPU acceleration ENABLED ({self.n_gpu_layers} layers offloaded)", flush=True)
        else:
            print(f"  ⚠ CPU mode (GPU disabled)", flush=True)

        # Grab raw pointers for hot-swap API
        self._model_ptr = self._llm._model.model
        self._ctx_ptr = self._llm._ctx.ctx

        # Pre-load all adapter handles
        behavioral_count = 0
        for name in self.available_adapters:
            path = str(ADAPTER_GGUF_MAP[name])
            is_behavioral = "behavioral" in path
            t = time.time()
            handle = llama_cpp.llama_adapter_lora_init(
                self._model_ptr, path.encode("utf-8")
            )
            if handle:
                self._adapter_handles[name] = handle
                tag = "BEHAVIORAL" if is_behavioral else "original"
                if is_behavioral:
                    behavioral_count += 1
                print(f"    {name} [{tag}] loaded ({time.time()-t:.2f}s)")
            else:
                print(f"    WARNING: failed to load {name} adapter handle")

        print(f"  {len(self._adapter_handles)}/{len(self.available_adapters)} "
              f"adapter handles ready ({behavioral_count} behavioral, "
              f"{len(self._adapter_handles) - behavioral_count} original)")

    def _load_model(self, adapter_name=None):
        """Switch to a specific adapter using instant hot-swap.

        Base model stays loaded — only the LoRA weights are swapped (~0ms).
        """
        if adapter_name == self._current_adapter:
            return  # Already active

        # Clear current adapter
        if self._ctx_ptr:
            llama_cpp.llama_clear_adapter_lora(self._ctx_ptr)

        # Apply new adapter if requested
        if adapter_name and adapter_name in self._adapter_handles:
            handle = self._adapter_handles[adapter_name]
            rc = llama_cpp.llama_set_adapter_lora(
                self._ctx_ptr, handle, ctypes.c_float(1.0)
            )
            if rc != 0:
                print(f"  WARNING: adapter {adapter_name} set failed (rc={rc})")

        self._current_adapter = adapter_name

        if self.verbose:
            label = adapter_name or "base"
            print(f"  [swapped to {label}]", flush=True)

    def set_memory_kernel(self, memory_kernel):
        """Attach a LivingMemoryKernel so cocoon knowledge enriches prompts."""
        self._memory_kernel = memory_kernel

    def _build_memory_context(self) -> str:
        """Build a memory context string from cocoon knowledge."""
        kernel = getattr(self, '_memory_kernel', None)
        if not kernel or not kernel.memories:
            return ""

        # Pull high-importance memories as context
        important = kernel.recall_important(min_importance=7)
        if not important:
            return ""

        lines = []
        for mem in important[:10]:  # Cap at 10 to avoid prompt bloat
            lines.append(f"- {mem.content}")

        return "\n\nCore knowledge from your memory:\n" + "\n".join(lines)

    def generate(self, query: str, adapter_name=None, system_prompt=None,
                 enable_tools=True):
        """Generate a response with autonomous self-correction.

        Pipeline:
        1. Extract constraints from query
        2. Detect chaos level (competing pressures)
        3. Build system prompt: chaos mitigation + constraint override + adapter + behavior lessons + memory
        4. Generate response
        5. Self-correction loop: detect violations → re-generate with correction prompt (max 1 retry)
        6. Post-process: enforce hard constraints as final safety net
        7. Record behavior (success/violation) for persistent learning

        User constraints (word limits, sentence limits, format rules) are
        extracted from the query and injected as the HIGHEST PRIORITY override
        in the system prompt — above adapter personality modes.
        """
        self._load_model(adapter_name)

        if system_prompt is None:
            system_prompt = ADAPTER_PROMPTS.get(adapter_name, ADAPTER_PROMPTS["_base"])

        # CONSTRAINT PRIORITY SYSTEM: Extract user constraints and inject as override
        constraints = extract_constraints(query)
        constraint_override = build_constraint_override(constraints)

        # CHAOS DETECTION: Detect competing pressures and apply mitigation
        chaos_mitigation = ""
        chaos_level = 0
        if constraints and SELF_CORRECTION_AVAILABLE:
            chaos_level, pressures = detect_chaos_level(query, constraints, adapter_name or "base")
            chaos_mitigation = build_chaos_mitigation(chaos_level, pressures)
            if self.verbose and chaos_level >= 2:
                print(f"  [CHAOS] Level {chaos_level}: {pressures}")

        # Build system prompt with priority layering:
        # [chaos mitigation] + [constraint override] + [adapter personality] + [behavior lessons] + [memory]
        if chaos_mitigation:
            system_prompt = chaos_mitigation + system_prompt
        if constraint_override:
            system_prompt = constraint_override + system_prompt
            if self.verbose:
                print(f"  [CONSTRAINTS] Detected: {constraints}")

        # PERSISTENT BEHAVIOR MEMORY: Inject lessons from past mistakes
        behavior_mem = _get_behavior_memory()
        if behavior_mem:
            lessons_prompt = behavior_mem.get_lessons_for_prompt(max_lessons=3)
            if lessons_prompt:
                system_prompt = system_prompt + lessons_prompt
                if self.verbose:
                    stats = behavior_mem.get_stats()
                    print(f"  [BEHAVIOR] {stats['total_lessons']} lessons loaded "
                          f"({stats['compliance_rate']:.0%} compliance)")

        # Enrich system prompt with cocoon memory knowledge
        memory_context = self._build_memory_context()
        if memory_context:
            system_prompt = system_prompt + memory_context

        # Augment system prompt with tool instructions
        if enable_tools:
            system_prompt = build_tool_system_prompt(system_prompt, _tool_registry)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        total_tokens = 0
        tool_results_log = []

        for round_num in range(MAX_TOOL_ROUNDS + 1):
            result = self._llm.create_chat_completion(
                messages=messages,
                **GEN_KWARGS,
            )

            text = result["choices"][0]["message"]["content"].strip()
            total_tokens += result["usage"]["completion_tokens"]

            # Check for tool calls
            if enable_tools and has_tool_calls(text):
                calls = parse_tool_calls(text)
                if calls and round_num < MAX_TOOL_ROUNDS:
                    # Execute tools
                    tool_output_parts = []
                    for tool_name, args, kwargs in calls:
                        print(f"  [tool] {tool_name}({args})")
                        result_text = _tool_registry.execute(tool_name, args, kwargs)
                        tool_output_parts.append(
                            f"<tool_result name=\"{tool_name}\">\n{result_text}\n</tool_result>"
                        )
                        tool_results_log.append({
                            "tool": tool_name,
                            "args": args,
                            "result_preview": result_text[:200],
                        })

                    # Add assistant's tool-calling message and tool results
                    messages.append({"role": "assistant", "content": text})
                    messages.append({
                        "role": "user",
                        "content": "Tool results:\n\n" + "\n\n".join(tool_output_parts)
                            + "\n\nNow provide your complete answer incorporating the tool results above. Do not call any more tools."
                    })

                    if self.verbose:
                        print(f"  [tool round {round_num + 1}] {len(calls)} tool(s) executed, re-generating...")
                    continue

            # No tool calls (or final round) — we're done
            # Strip any leftover tool tags from final response
            clean_text = strip_tool_calls(text) if has_tool_calls(text) else text
            break

        # SELF-CORRECTION LOOP: Detect violations and re-generate if needed (max 1 retry)
        self_corrected = False
        if constraints and SELF_CORRECTION_AVAILABLE:
            violations = detect_violations(clean_text, constraints)
            if violations:
                if self.verbose:
                    print(f"  [SELF-CORRECT] Violations detected: {violations}")
                    print(f"  [SELF-CORRECT] Re-generating with correction prompt...")

                # Build correction prompt and re-generate
                correction = build_correction_prompt(clean_text, violations, constraints, query)
                messages.append({"role": "assistant", "content": clean_text})
                messages.append({"role": "user", "content": correction})

                retry_result = self._llm.create_chat_completion(
                    messages=messages,
                    **GEN_KWARGS,
                )
                retry_text = retry_result["choices"][0]["message"]["content"].strip()
                total_tokens += retry_result["usage"]["completion_tokens"]

                # Check if retry is better
                retry_violations = detect_violations(retry_text, constraints)
                if len(retry_violations) < len(violations):
                    clean_text = retry_text
                    self_corrected = True
                    if self.verbose:
                        remaining = retry_violations if retry_violations else "none"
                        print(f"  [SELF-CORRECT] Retry improved: {remaining}")
                elif not retry_violations:
                    clean_text = retry_text
                    self_corrected = True
                    if self.verbose:
                        print(f"  [SELF-CORRECT] Retry passed all constraints")
                else:
                    if self.verbose:
                        print(f"  [SELF-CORRECT] Retry didn't improve, using post-processor")

        # POST-PROCESSING: Enforce hard constraints as final safety net
        if constraints:
            clean_text = enforce_constraints(clean_text, constraints)
            if self.verbose:
                print(f"  [CONSTRAINTS] Post-enforcement applied: {constraints}")

        # PERMANENT LOCKS: Universal self-check on EVERY response (constrained or not)
        if SELF_CORRECTION_AVAILABLE:
            clean_text, lock_issues = universal_self_check(clean_text)
            if lock_issues and self.verbose:
                print(f"  [LOCKS] Applied: {lock_issues}")

            # If self-check returned empty (echo-back failure), re-generate with direct instruction
            if not clean_text.strip() and any("LOCK3_FAIL" in i for i in lock_issues):
                if self.verbose:
                    print(f"  [LOCKS] Echo-back detected, re-generating with direct prompt...")
                retry_messages = [
                    {"role": "system", "content": ADAPTER_PROMPTS.get(adapter_name, ADAPTER_PROMPTS["_base"])},
                    {"role": "user", "content": f"Answer this question directly. Do NOT echo it back. Just give the answer:\n{query}"},
                ]
                retry_result = self._llm.create_chat_completion(messages=retry_messages, **GEN_KWARGS)
                clean_text = retry_result["choices"][0]["message"]["content"].strip()
                total_tokens += retry_result["usage"]["completion_tokens"]
                # Run locks again on retry
                clean_text, _ = universal_self_check(clean_text)
                # Re-apply constraints if needed
                if constraints:
                    clean_text = enforce_constraints(clean_text, constraints)

        # BEHAVIOR MEMORY: Record outcome for persistent learning
        if constraints and behavior_mem:
            try:
                final_violations = detect_violations(clean_text, constraints) if SELF_CORRECTION_AVAILABLE else []
                if final_violations:
                    behavior_mem.record_violation(
                        query=query,
                        constraints=constraints,
                        violations=final_violations,
                        adapter=adapter_name or "base",
                        response_preview=clean_text,
                    )
                else:
                    behavior_mem.record_success(
                        query=query,
                        constraints=constraints,
                        adapter=adapter_name or "base",
                        word_count=len(clean_text.split()),
                    )
            except Exception:
                pass  # Non-critical

        return clean_text, total_tokens, tool_results_log

    def _needs_tools(self, query: str) -> bool:
        """Detect if a query is asking about the Codette PROJECT/CODEBASE.

        Only trigger tools for questions about the project itself, not for
        general domain questions like 'How does gravity work?'.
        """
        q = query.lower()

        # Must mention the project/codebase context explicitly
        project_anchors = [
            "codette", "this project", "the project", "the codebase",
            "this repo", "the repo", "our code", "the code",
            "show me the", "read the file", "read file",
            "what files", "which files", "list files",
        ]
        has_project_context = any(anchor in q for anchor in project_anchors)

        # Specific code/project keywords (only trigger WITH project context)
        code_keywords = [
            "pipeline", "config", "adapter", "dataset", "directory",
            "folder", "source", "script", "implementation",
            "server", "forge", "spiderweb", "cocoon",
        ]

        # Strong triggers that always mean "look at the codebase"
        strong_triggers = [
            "show me the code", "read the file", "what's in the",
            "look at the file", "open the file", "search the code",
            "project structure", "project summary", "file structure",
            "what files", "which files", "list files", "list the",
        ]

        if any(t in q for t in strong_triggers):
            return True

        if has_project_context and any(kw in q for kw in code_keywords):
            return True

        return False

    def _auto_gather_context(self, query: str) -> str:
        """Server-side tool execution: gather relevant file context BEFORE
        sending to the model, so the model doesn't need to call tools itself.

        This is the reliable approach for small models that can't do
        structured tool calling consistently.
        """
        q = query.lower()
        context_parts = []

        # Map query keywords to automatic tool calls
        auto_lookups = []

        if any(k in q for k in ["pipeline", "training", "train"]):
            auto_lookups.append(("read_file", ["scripts/run_full_pipeline.py", 1, 60]))
            auto_lookups.append(("read_file", ["configs/adapter_registry.yaml", 1, 51]))

        if any(k in q for k in ["adapter", "lora", "perspective"]):
            auto_lookups.append(("read_file", ["configs/adapter_registry.yaml", 1, 51]))

        if any(k in q for k in ["config", "setting"]):
            auto_lookups.append(("read_file", ["configs/adapter_registry.yaml", 1, 51]))
            auto_lookups.append(("list_files", ["configs/"]))

        if any(k in q for k in ["architecture", "structure", "project", "overview"]):
            auto_lookups.append(("project_summary", []))

        if any(k in q for k in ["server", "web", "ui", "interface"]):
            auto_lookups.append(("read_file", ["inference/codette_server.py", 1, 50]))

        if any(k in q for k in ["spiderweb", "cocoon", "quantum"]):
            auto_lookups.append(("read_file", ["reasoning_forge/quantum_spiderweb.py", 1, 50]))

        if any(k in q for k in ["epistemic", "tension", "coherence", "metric"]):
            auto_lookups.append(("read_file", ["reasoning_forge/epistemic_metrics.py", 1, 50]))

        if any(k in q for k in ["dataset", "data"]):
            auto_lookups.append(("list_files", ["datasets/", "*.jsonl"]))

        if any(k in q for k in ["paper", "research", "publication"]):
            auto_lookups.append(("file_info", ["paper/codette_paper.pdf"]))
            auto_lookups.append(("read_file", ["paper/codette_paper.tex", 1, 40]))

        if any(k in q for k in ["forge", "reasoning", "agent"]):
            auto_lookups.append(("list_files", ["reasoning_forge/"]))
            auto_lookups.append(("read_file", ["reasoning_forge/epistemic_metrics.py", 1, 40]))

        # If no specific match, do a code search
        if not auto_lookups:
            # Extract key terms for search
            skip = {"show", "me", "the", "what", "is", "how", "does", "where",
                    "can", "you", "tell", "about", "look", "at", "find", "check"}
            terms = [w for w in q.split() if w not in skip and len(w) > 2]
            if terms:
                auto_lookups.append(("search_code", [terms[0]]))

        # Execute lookups
        tool_log = []
        for tool_name, args in auto_lookups[:3]:  # Max 3 lookups
            print(f"  [auto-tool] {tool_name}({args})")
            result = _tool_registry.execute(tool_name, args, {})
            context_parts.append(f"=== {tool_name}({', '.join(str(a) for a in args)}) ===\n{result}")
            tool_log.append({"tool": tool_name, "args": args, "result_preview": result[:200]})

        context = "\n\n".join(context_parts)
        return context, tool_log

    def route_and_generate(self, query: str, max_adapters=2,
                           strategy="keyword", force_adapter=None):
        """The main entry point: route query, select adapter(s), generate."""

        # Force a specific adapter if requested
        if force_adapter:
            route = RouteResult(
                primary=force_adapter,
                confidence=1.0,
                reasoning=f"Forced: {force_adapter}",
                strategy="forced",
            )
        else:
            route = self.router.route(query, strategy=strategy,
                                      max_adapters=max_adapters)

        print(f"\n  Route: {' + '.join(route.all_adapters)} "
              f"(conf={route.confidence:.2f}, {route.strategy})")
        if self.verbose:
            print(f"  Reason: {route.reasoning}")

        # Multi-perspective first (most important routing decision)
        if route.multi_perspective and len(route.all_adapters) > 1:
            return self._multi_perspective_generate(query, route)

        # Only use tools for explicit codebase/project queries
        if self._needs_tools(query):
            print(f"  [project query — auto-gathering context]")
            return self._tool_augmented_generate(query, route)

        return self._single_generate(query, route)

    def _tool_augmented_generate(self, query: str, route: RouteResult):
        """Generate with auto-gathered file context injected into the prompt."""
        start = time.time()

        # Gather context server-side (reliable, no model cooperation needed)
        context, tool_log = self._auto_gather_context(query)

        # Build augmented query with context
        augmented_query = f"""The user asked: {query}

Here is relevant project context to help you answer:

{context}

Based on the context above, answer the user's question. Reference specific files, line numbers, and code when relevant. Be specific and factual."""

        # Generate with context (disable model-side tools since we did it server-side)
        text, tokens, _ = self.generate(augmented_query, route.primary, enable_tools=False)
        elapsed = time.time() - start
        tps = tokens / elapsed if elapsed > 0 else 0

        print(f"  [{route.primary}] ({tokens} tok, {tps:.1f} tok/s)")
        if tool_log:
            print(f"  [auto-tools: {', '.join(t['tool'] for t in tool_log)}]")

        return {
            "response": text,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": elapsed,
            "tools_used": tool_log,
        }

    def _single_generate(self, query: str, route: RouteResult):
        """Generate with a single adapter."""
        start = time.time()
        text, tokens, tool_log = self.generate(query, route.primary, enable_tools=False)
        elapsed = time.time() - start
        tps = tokens / elapsed if elapsed > 0 else 0

        print(f"  [{route.primary}] ({tokens} tok, {tps:.1f} tok/s)")
        if tool_log:
            print(f"  [tools used: {', '.join(t['tool'] for t in tool_log)}]")
        return {
            "response": text,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": elapsed,
            "tools_used": tool_log,
        }

    def _multi_perspective_generate(self, query: str, route: RouteResult):
        """Generate with multiple adapters and synthesize."""
        perspectives = {}
        total_tokens = 0
        total_time = 0

        for adapter_name in route.all_adapters:
            if adapter_name not in self.available_adapters:
                print(f"  [{adapter_name}] SKIPPED (not available)")
                continue

            start = time.time()
            text, tokens, _tool_log = self.generate(query, adapter_name,
                                                     enable_tools=False)
            elapsed = time.time() - start
            tps = tokens / elapsed if elapsed > 0 else 0
            total_tokens += tokens
            total_time += elapsed

            perspectives[adapter_name] = text
            print(f"  [{adapter_name}] ({tokens} tok, {tps:.1f} tok/s)")

        # Synthesize if we got multiple perspectives
        if len(perspectives) > 1:
            print(f"  [synthesizing...]")
            synthesis = self._synthesize(query, perspectives)
        elif perspectives:
            synthesis = list(perspectives.values())[0]
        else:
            synthesis = "No adapters available for this query."

        return {
            "response": synthesis,
            "perspectives": perspectives,
            "adapters": list(perspectives.keys()),
            "route": route,
            "tokens": total_tokens,
            "time": total_time,
        }

    def _synthesize(self, query: str, perspectives: dict):
        """Combine multiple perspective responses into a unified answer.

        Enhanced with DreamReweaver creative bridges when available.
        Truncates perspectives to fit within context window.
        """
        # Truncate each perspective to fit within context budget
        # Reserve ~1200 tokens for system prompt + synthesis output
        max_per_perspective = max(200, (self.n_ctx - 1200) // max(len(perspectives), 1))
        # Rough char estimate: 1 token ~ 4 chars
        max_chars = max_per_perspective * 4

        combined = "\n\n".join(
            f"**{name.upper()} PERSPECTIVE:**\n{text[:max_chars]}"
            for name, text in perspectives.items()
        )

        # Try DreamReweaver creative framing (VIVARA enhancement)
        dream_frame = ""
        try:
            from reasoning_forge.dream_reweaver import DreamReweaver
            dreamer = DreamReweaver(creativity=0.3)
            dream = dreamer.synthesize(perspectives, query=query)
            if dream.creative_frame:
                dream_frame = f"\n\nCreative synthesis guidance:\n{dream.creative_frame}\n"
        except Exception:
            pass  # Graceful fallback — works without DreamReweaver

        synthesis_prompt = f"""You received this question: "{query}"

Multiple reasoning perspectives have weighed in:

{combined}
{dream_frame}
Synthesize these perspectives into a single, coherent response that:
1. Preserves the unique insights from each perspective
2. Notes where perspectives complement or tension each other
3. Arrives at a richer understanding than any single view

Synthesized response:"""

        # Use base model for synthesis (no adapter bias)
        self._load_model(None)
        result = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": ADAPTER_PROMPTS["multi_perspective"]},
                {"role": "user", "content": synthesis_prompt},
            ],
            max_tokens=1024,
            temperature=0.7,
            top_p=0.9,
            stop=["<|eot_id|>", "<|end_of_text|>"],
        )

        return result["choices"][0]["message"]["content"].strip()


# ================================================================
# Interactive Chat Mode
# ================================================================
def interactive_chat(orchestrator, max_adapters=2, strategy="keyword"):
    """Run Codette as an interactive chatbot."""
    print("\n" + "=" * 60)
    print("  CODETTE ORCHESTRATOR — Interactive Mode")
    print("=" * 60)
    print(f"  Strategy: {strategy} | Max adapters: {max_adapters}")
    print(f"  Available: {', '.join(orchestrator.available_adapters)}")
    print(f"  Commands: /quit, /adapter <name>, /multi <n>, /base, /verbose")
    print("=" * 60)

    while True:
        try:
            query = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue

        # Commands
        if query.startswith("/"):
            parts = query.split()
            cmd = parts[0].lower()

            if cmd in ("/quit", "/exit", "/q"):
                print("Goodbye!")
                break
            elif cmd == "/adapter" and len(parts) > 1:
                force = parts[1]
                result = orchestrator.route_and_generate(
                    input("  Query: ").strip(),
                    force_adapter=force,
                )
                print(f"\nCodette ({force}):\n{result['response']}")
                continue
            elif cmd == "/multi" and len(parts) > 1:
                max_adapters = int(parts[1])
                print(f"  Max adapters set to {max_adapters}")
                continue
            elif cmd == "/base":
                result = orchestrator.route_and_generate(
                    input("  Query: ").strip(),
                    force_adapter=None,
                )
                print(f"\nCodette (base):\n{result['response']}")
                continue
            elif cmd == "/verbose":
                orchestrator.verbose = not orchestrator.verbose
                print(f"  Verbose: {orchestrator.verbose}")
                continue
            else:
                print("  Unknown command. Try /quit, /adapter <name>, /multi <n>, /base, /verbose")
                continue

        # Normal query — route and generate
        result = orchestrator.route_and_generate(
            query,
            max_adapters=max_adapters,
            strategy=strategy,
        )

        print(f"\nCodette:")
        print(result["response"])

        # Show perspectives if multi
        if "perspectives" in result and len(result.get("perspectives", {})) > 1:
            show = input("\n  Show individual perspectives? (y/n): ").strip().lower()
            if show == "y":
                for name, text in result["perspectives"].items():
                    print(f"\n  [{name.upper()}]:")
                    print(f"  {text}")


# ================================================================
# Main
# ================================================================
def main():
    parser = argparse.ArgumentParser(description="Codette Orchestrator")
    parser.add_argument("--query", "-q", type=str, help="Single query (non-interactive)")
    parser.add_argument("--adapter", "-a", type=str, help="Force specific adapter")
    parser.add_argument("--multi", "-m", type=int, default=2, help="Max adapters (default: 2)")
    parser.add_argument("--strategy", "-s", type=str, default="keyword",
                        choices=["keyword", "llm", "hybrid"], help="Routing strategy")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--gpu-layers", type=int, default=0, help="GPU layers (0=CPU only)")
    args = parser.parse_args()

    print("=" * 60)
    print("  CODETTE ORCHESTRATOR")
    print("=" * 60)
    print(f"  Base: {os.path.basename(BASE_GGUF)}")
    print(f"  Strategy: {args.strategy}")

    orchestrator = CodetteOrchestrator(
        n_gpu_layers=args.gpu_layers,
        verbose=args.verbose,
    )

    if args.query:
        # Single query mode
        result = orchestrator.route_and_generate(
            args.query,
            max_adapters=args.multi,
            strategy=args.strategy,
            force_adapter=args.adapter,
        )
        print(f"\nCodette:")
        print(result["response"])

        if "perspectives" in result:
            print(f"\n--- Perspectives ---")
            for name, text in result["perspectives"].items():
                print(f"\n[{name.upper()}]:")
                print(text)
    else:
        # Interactive chat mode
        interactive_chat(orchestrator, max_adapters=args.multi, strategy=args.strategy)


if __name__ == "__main__":
    main()
