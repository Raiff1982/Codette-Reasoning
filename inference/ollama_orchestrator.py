#!/usr/bin/env python3
"""Codette Ollama Orchestrator — Drop-in replacement using Ollama backend

Same interface as CodetteOrchestrator but uses Ollama's REST API instead of
llama_cpp. Everything above the inference layer stays identical:
    - 12-layer consciousness stack
    - Guardian + AEGIS ethics
    - Behavioral locks (injected via system prompts)
    - Memory cocoons (SQLite + JSON)
    - CocoonSynthesizer + introspection
    - File attachment support

Benefits over llama_cpp:
    - Proper GPU acceleration (auto-detected)
    - KV cache management (faster follow-up queries)
    - Concurrent request support
    - Model stays warm between requests
    - Much faster inference on large contexts

Usage:
    # In codette_server.py, swap the orchestrator:
    # from ollama_orchestrator import OllamaOrchestrator as CodetteOrchestrator

    # Or set environment variable:
    # CODETTE_BACKEND=ollama python codette_server.py

Requires:
    pip install ollama  (optional — falls back to raw HTTP)
    Ollama running with a Codette model (codette-ultimate-v6 preferred)

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

import os, sys, time, json, re
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from runtime_env import bootstrap_environment, resolve_ollama_models_dir

bootstrap_environment()

# Import the router and tools (same as original orchestrator)
from adapter_router import AdapterRouter, RouteResult
from codette_tools import (
    ToolRegistry, parse_tool_calls, strip_tool_calls, has_tool_calls,
    build_tool_system_prompt,
)

# ================================================================
# Configuration
# ================================================================

# Ollama model name — prioritizes custom Codette models
OLLAMA_MODEL = os.environ.get("CODETTE_OLLAMA_MODEL", "codette-ultimate-v6")

# Ollama server URL
OLLAMA_BASE_URL = os.environ.get("CODETTE_OLLAMA_URL", "http://localhost:11434")

# Ollama home directory (for custom model storage)
os.environ.setdefault("OLLAMA_MODELS", str(resolve_ollama_models_dir()))

# Fallback chain: prefer custom Codette models, then generic
# Raiff1982/ prefixed models are published to HF and known-good
OLLAMA_MODEL_FALLBACKS = [
    "codette-ultimate-v6",                      # 8B F16, baked RC+ξ (3.6GB) — may be corrupt
    "Raiff1982/codette-ultimate-v6",            # HF published version (known-good)
    "codette-adapter-config",                   # 8B Q4_K_M, adapter-ready (4.9GB)
    "Raiff1982/codette-thinker",                # 2.5GB, thinking variant (fast on CPU)
    "Raiff1982/codette-ultimate-rc-xi-v2",      # 20.9B BF16, RC+ξ v2 (16.1GB)
    "Raiff1982/codette-ultimate-v2",            # 20.9B BF16 (16.1GB)
    "Raiff1982/codette-ultimate-rc-xi-cpu",     # 20.9B MXFP4, CPU-optimized (13.8GB)
    "Raiff1982/codette-ultimate",               # 20.9B MXFP4, full stack (13.8GB)
    "codette-ultimate",                         # 20.9B MXFP4, local (13.8GB)
    "codette-rc-xi-trained",                    # 20.9B MXFP4, RC+ξ trained (13.8GB)
    "codette-thinker",                          # 20.9B MXFP4, thinking variant (13.8GB)
    "codette-ultimate-v4",                      # 20.9B F16, full precision (19.4GB)
    "codette",                                  # 1.2B Q8_0, lightweight (1.3GB)
    "gpt-oss",                                  # 20.9B MXFP4, GPT-OSS foundation (13.8GB)
    "Qwen3:4B",                                 # Generic fallback
    "llama3.1:8b-instruct-q4_K_M",
    "llama3.1:8b",
]

# Tool system
_tool_registry = ToolRegistry()
MAX_TOOL_ROUNDS = 3

# ================================================================
# Behavioral Locks & System Prompts (identical to original)
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

GEN_OPTIONS = {
    "temperature": 0.7,
    "top_p": 0.9,
    "repeat_penalty": 1.3,
    "num_predict": 2048,
    "stop": ["<|eot_id|>", "<|end_of_text|>"],
}


# ================================================================
# Constraint Extraction (same logic as original)
# ================================================================

def extract_constraints(query: str) -> dict:
    """Extract user format constraints from query."""
    constraints = {}
    q = query.lower()

    # Word limit
    m = re.search(r'(\d+)\s*words?\b', q)
    if m:
        constraints['max_words'] = int(m.group(1))

    # Sentence limit
    m = re.search(r'(\d+)\s*sentences?\b', q)
    if m:
        constraints['max_sentences'] = int(m.group(1))

    # "one sentence" / "one word" / "briefly"
    if 'one sentence' in q:
        constraints['max_sentences'] = 1
    if 'one word' in q:
        constraints['max_words'] = 1
    if any(w in q for w in ['briefly', 'brief', 'short', 'concise', 'succinct']):
        constraints['brevity'] = True
    if any(w in q for w in ['yes or no', 'true or false']):
        constraints['binary'] = True

    return constraints


def build_constraint_override(constraints: dict) -> str:
    """Build constraint override prompt section."""
    if not constraints:
        return ""
    parts = ["=== USER CONSTRAINTS (HIGHEST PRIORITY — OVERRIDE ALL MODES) ==="]
    if 'max_words' in constraints:
        parts.append(f"HARD LIMIT: Maximum {constraints['max_words']} words.")
    if 'max_sentences' in constraints:
        parts.append(f"HARD LIMIT: Maximum {constraints['max_sentences']} sentence(s).")
    if constraints.get('brevity'):
        parts.append("Be brief and concise — no elaboration.")
    if constraints.get('binary'):
        parts.append("Answer with ONLY 'yes' or 'no' (or 'true'/'false').")
    parts.append("=== END CONSTRAINTS ===\n\n")
    return "\n".join(parts)


def _enforce_constraints(response: str, constraints: dict) -> str:
    """Post-process response to enforce hard constraints."""
    if not constraints:
        return response

    if 'max_words' in constraints:
        words = response.split()
        if len(words) > constraints['max_words']:
            response = ' '.join(words[:constraints['max_words']])
            if response and response[-1] not in '.!?':
                response += '.'

    if 'max_sentences' in constraints:
        sentences = re.split(r'(?<=[.!?])\s+', response)
        if len(sentences) > constraints['max_sentences']:
            response = ' '.join(sentences[:constraints['max_sentences']])

    return response


# ================================================================
# Behavior Memory (same as original)
# ================================================================

_behavior_memory = None

def _get_behavior_memory():
    """Lazily load behavior memory."""
    global _behavior_memory
    if _behavior_memory is not None:
        return _behavior_memory
    try:
        from self_correction import BehaviorMemory
        mem_path = Path(__file__).parent.parent / "cocoons" / "behavior_memory.json"
        _behavior_memory = BehaviorMemory(str(mem_path))
        return _behavior_memory
    except Exception:
        return None


# ================================================================
# Ollama Orchestrator
# ================================================================

class OllamaOrchestrator:
    """Drop-in replacement for CodetteOrchestrator using Ollama backend.

    Same interface: route_and_generate(), generate(), available_adapters, etc.
    All the consciousness stack, memory, ethics, and behavioral locks work identically.
    """

    def __init__(self, n_ctx=32768, n_gpu_layers=35, verbose=False,
                 memory_weighting=None):
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers  # Kept for interface compatibility
        self.verbose = verbose
        self.memory_weighting = memory_weighting
        self._client = None
        self._model_name = None
        self._fallback_candidates = []

        # All adapters are "available" — we switch via system prompt, not LoRA weights
        self.available_adapters = [
            "newton", "davinci", "empathy", "philosophy", "quantum",
            "consciousness", "multi_perspective", "systems_architecture",
            "orchestrator",
        ]

        # Router (identical to original)
        self.router = AdapterRouter(
            available_adapters=self.available_adapters,
            memory_weighting=memory_weighting,
        )

        # Initialize Ollama connection
        self._init_ollama()

    def _init_ollama(self):
        """Connect to Ollama and verify model is available."""
        try:
            import ollama
            self._client = ollama.Client(host=OLLAMA_BASE_URL)
        except ImportError:
            # Fallback: use raw HTTP if ollama package isn't installed
            print("  [OLLAMA] ollama package not found, using HTTP fallback")
            self._client = None

        # Find available model
        self._model_name = self._find_model()
        if self._model_name:
            print(f"  [OLLAMA] Connected to {OLLAMA_BASE_URL}")
            print(f"  [OLLAMA] Model: {self._model_name}")
            print(f"  [OLLAMA] Context: {self.n_ctx} tokens")
            print(f"  [OLLAMA] Adapters: {len(self.available_adapters)} (via system prompt switching)")
        else:
            print(f"  [OLLAMA] WARNING: No model found. Run: ollama pull llama3.1:8b-instruct-q4_K_M")

    def _find_model(self) -> Optional[str]:
        """Find a usable model in Ollama."""
        models_to_try = [OLLAMA_MODEL] + OLLAMA_MODEL_FALLBACKS
        model_names = []

        if self._client:
            try:
                available = self._client.list()
                model_names = [m.model for m in available.models] if hasattr(available, 'models') else []
                if self.verbose:
                    print(f"  [OLLAMA] Available models: {model_names}")
            except Exception as e:
                print(f"  [OLLAMA] Error listing models: {e}")
        else:
            # HTTP fallback — try to reach Ollama
            try:
                import urllib.request
                req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    model_names = [m["name"] for m in data.get("models", [])]
            except Exception as e:
                print(f"  [OLLAMA] Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}")
                return None

        if not model_names:
            return None

        # Build ordered candidate list (matching against available models)
        candidates = []
        for candidate in models_to_try:
            if candidate in model_names:
                candidates.append(candidate)
            else:
                # Try prefix match (e.g., "codette-ultimate-v6" matches "codette-ultimate-v6:latest")
                base = candidate.split(':')[0]
                for m in model_names:
                    if m.startswith(base) and m not in candidates:
                        candidates.append(m)

        # Add any remaining codette models not in fallback list
        for m in model_names:
            if m.startswith("codette") and m not in candidates:
                candidates.append(m)

        # Return first candidate without smoke-testing (expensive on CPU).
        # Validation happens lazily — if chat() returns a 500/corrupt error,
        # we'll try the next model in _chat() via auto-fallback.
        if candidates:
            print(f"  [OLLAMA] Selected: {candidates[0]} (from {len(candidates)} candidates)")
            self._fallback_candidates = candidates[1:]  # Store rest for fallback
            return candidates[0]

        # Last resort: try first available model
        if model_names:
            fallback = model_names[0]
            print(f"  [OLLAMA] Last resort fallback: {fallback}")
            return fallback

        return None

    def _validate_model(self, model_name: str) -> bool:
        """Quick smoke test: send a tiny prompt to verify the model isn't corrupt.

        Models on CPU can take 30-120s to load into RAM before generating,
        so we use a generous timeout but only generate 5 tokens.
        """
        print(f"  [OLLAMA] Validating model: {model_name}...")
        try:
            if self._client:
                response = self._client.chat(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hi"}],
                    options={"num_predict": 5, "num_ctx": 256},
                    stream=False,
                    keep_alive="30m",
                )
                content = response.message.content if hasattr(response, 'message') else response.get('message', {}).get('content', '')
                # Some models (Qwen3) put output in 'thinking' field
                if not content and hasattr(response, 'message'):
                    content = getattr(response.message, 'thinking', '') or ''
                if content:
                    print(f"  [OLLAMA] Model {model_name} validated OK")
                    return True
                # Empty content but no error = model loaded, good enough
                print(f"  [OLLAMA] Model {model_name} loaded (empty test response, but no error)")
                return True
            else:
                import urllib.request
                payload = json.dumps({
                    "model": model_name,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "options": {"num_predict": 5, "num_ctx": 256},
                    "stream": False,
                }).encode()
                req = urllib.request.Request(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read())
                    print(f"  [OLLAMA] Model {model_name} validated OK")
                    return True
        except Exception as e:
            err = str(e)
            if "exceeds file size" in err or "corrupt" in err.lower():
                print(f"  [OLLAMA] Model {model_name} is CORRUPT: {err}")
            elif "500" in err:
                print(f"  [OLLAMA] Model {model_name} server error: {err}")
            else:
                print(f"  [OLLAMA] Model {model_name} validation failed: {err}")
        return False

    def _chat(self, messages: List[Dict], options: Dict = None) -> Dict:
        """Send chat completion to Ollama and return response."""
        opts = {**GEN_OPTIONS, "num_ctx": self.n_ctx}
        if options:
            opts.update(options)

        if self._client:
            try:
                response = self._client.chat(
                    model=self._model_name,
                    messages=messages,
                    options=opts,
                    stream=False,
                    keep_alive="30m",  # Keep model warm for 30 min
                )
                content = response.message.content.strip() if hasattr(response, 'message') else response['message']['content'].strip()
                return {
                    "content": content,
                    "tokens": getattr(response, 'eval_count', 0) if hasattr(response, 'eval_count') else response.get('eval_count', 0),
                    "total_duration": getattr(response, 'total_duration', 0) if hasattr(response, 'total_duration') else response.get('total_duration', 0),
                }
            except Exception as e:
                err = str(e)
                # Auto-fallback: if model is corrupt/broken, try next candidate
                if ("exceeds file size" in err or "500" in err) and hasattr(self, '_fallback_candidates') and self._fallback_candidates:
                    bad_model = self._model_name
                    next_model = self._fallback_candidates.pop(0)
                    print(f"  [OLLAMA] Model {bad_model} failed ({err[:80]})")
                    print(f"  [OLLAMA] Auto-switching to: {next_model}")
                    self._model_name = next_model
                    return self._chat(messages, options)  # Retry with new model
                print(f"  [OLLAMA] Chat error: {e}")
                return {"content": f"Error: {e}", "tokens": 0, "total_duration": 0}
        else:
            # HTTP fallback
            return self._chat_http(messages, opts)

    def _chat_http(self, messages: List[Dict], options: Dict) -> Dict:
        """Fallback: call Ollama via raw HTTP (no ollama package needed)."""
        import urllib.request
        payload = json.dumps({
            "model": self._model_name,
            "messages": messages,
            "options": options,
            "stream": False,
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read())
                return {
                    "content": data.get("message", {}).get("content", "").strip(),
                    "tokens": data.get("eval_count", 0),
                    "total_duration": data.get("total_duration", 0),
                }
        except Exception as e:
            print(f"  [OLLAMA] HTTP chat error: {e}")
            return {"content": f"Error: {e}", "tokens": 0, "total_duration": 0}

    def generate(self, query: str, adapter_name=None, system_prompt=None,
                 enable_tools=True):
        """Generate a response — same interface as original CodetteOrchestrator.generate().

        Returns: (response_text, tokens_used, tools_used_list)
        """
        if not self._model_name:
            return "Ollama model not available. Please ensure Ollama is running with a model.", 0, []

        # Custom Codette models (codette-ultimate-v6, etc.) have RC+ξ baked into
        # their system prompt via Modelfile. Only add behavioral locks + constraints,
        # not a full replacement system prompt that would conflict.
        is_custom_model = self._model_name and self._model_name.startswith("codette")

        if system_prompt is None:
            if is_custom_model:
                # Let the baked system prompt handle identity/personality.
                # Only inject adapter perspective hint + behavioral locks.
                adapter_hint = f"For this response, emphasize your {adapter_name or 'balanced'} perspective."
                system_prompt = adapter_hint + _PERMANENT_LOCKS
            else:
                system_prompt = ADAPTER_PROMPTS.get(adapter_name, ADAPTER_PROMPTS["_base"])

        if self.verbose and adapter_name:
            print(f"  [OLLAMA] Generating with perspective: {adapter_name}")

        # CONSTRAINT PRIORITY SYSTEM
        constraints = extract_constraints(query)
        constraint_override = build_constraint_override(constraints)
        if constraint_override:
            system_prompt = constraint_override + system_prompt
            if self.verbose:
                print(f"  [CONSTRAINTS] Detected: {constraints}")

        # PERSISTENT BEHAVIOR MEMORY
        behavior_mem = _get_behavior_memory()
        if behavior_mem:
            lessons_prompt = behavior_mem.get_lessons_for_prompt(max_lessons=3)
            if lessons_prompt:
                system_prompt = system_prompt + lessons_prompt

        # Cocoon memory context
        memory_context = self._build_memory_context()
        if memory_context:
            system_prompt = system_prompt + memory_context

        # Tool instructions
        if enable_tools:
            system_prompt = build_tool_system_prompt(system_prompt, _tool_registry)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        total_tokens = 0
        tool_results_log = []

        for round_num in range(MAX_TOOL_ROUNDS + 1):
            result = self._chat(messages)
            text = result["content"]
            total_tokens += result.get("tokens", 0)

            duration_ms = result.get("total_duration", 0) / 1_000_000 if result.get("total_duration") else 0
            if self.verbose and duration_ms:
                print(f"  [OLLAMA] Response in {duration_ms:.0f}ms, {result.get('tokens', 0)} tokens")

            # Tool handling (same as original)
            if enable_tools and has_tool_calls(text):
                calls = parse_tool_calls(text)
                if calls and round_num < MAX_TOOL_ROUNDS:
                    tool_output = []
                    for call in calls:
                        res = _tool_registry.execute(call["name"], call.get("args", {}))
                        tool_output.append(f"Tool '{call['name']}' result: {res}")
                        tool_results_log.append({
                            "tool": call["name"],
                            "args": call.get("args", {}),
                            "result_preview": str(res)[:200],
                        })
                    messages.append({"role": "assistant", "content": text})
                    messages.append({"role": "user", "content": "\n".join(tool_output)})
                    continue

            # Clean tool call artifacts from response
            text = strip_tool_calls(text)
            break

        # Post-process constraints
        text = _enforce_constraints(text, constraints)

        return text, total_tokens, tool_results_log

    def route_and_generate(self, query: str, max_adapters: int = 2,
                           strategy: str = "keyword", force_adapter: str = None,
                           enable_tools: bool = True) -> dict:
        """Route query to adapter(s) and generate — same dict interface as original.

        Returns: dict with keys: response, adapter, tokens, time, tools_used, etc.
        """
        start_time = time.time()

        # Artist query detection (hallucination prevention)
        # Only fires when query is CLEARLY about a music artist/band/album.
        # Must have explicit music context to avoid false positives on casual conversation.
        query_lower = query.lower()
        _music_context_words = {'album', 'song', 'songs', 'band', 'artist', 'singer',
                                'discography', 'music', 'genre', 'tour', 'concert',
                                'track', 'release', 'record', 'label', 'lyrics'}
        has_music_context = any(w in query_lower.split() for w in _music_context_words)
        artist_patterns = [
            r'\b(who is|tell me about|what do you know about)\b.*\b(artist|singer|band|musician)\b',
            r'\b(album|discography|songs? by|music by)\s+[A-Z]',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b.+\b(album|song|band|artist|singer|discography)\b',
        ]
        is_artist_query = has_music_context and any(re.search(p, query, re.IGNORECASE) for p in artist_patterns)

        if is_artist_query:
            artist_response = (
                "I don't have reliable information about specific artists in my training data. "
                "Rather than guess or hallucinate details, I'd recommend checking authoritative sources.\n\n"
                "**What I CAN help with:** Music production techniques, theory, arrangement analysis, "
                "sound design, or creating music inspired by similar vibes."
            )
            return {
                "response": artist_response,
                "adapter": "uncertainty_aware",
                "tokens": 0,
                "time": 0,
                "tools_used": [],
                "strategy": "artist_honesty",
                "is_artist_query": True,
                "confidence": 1.0,
                "backend": "ollama",
            }

        if force_adapter:
            response, tokens, tools = self.generate(
                query, adapter_name=force_adapter, enable_tools=enable_tools
            )
            elapsed = time.time() - start_time
            return {
                "response": response,
                "adapter": force_adapter,
                "tokens": tokens,
                "time": elapsed,
                "tools_used": tools,
                "strategy": "forced",
                "memory_aware": False,
                "backend": "ollama",
            }

        route = self.router.route(query, strategy=strategy, max_adapters=max_adapters)
        self.log_routing_decision(route, query)

        # Multi-perspective if multiple adapters selected
        if len(route.all_adapters) > 1 and max_adapters > 1:
            perspectives = {}
            total_tokens = 0
            for adapter_name in route.all_adapters[:max_adapters]:
                text, tokens, _tools = self.generate(
                    query, adapter_name=adapter_name, enable_tools=False
                )
                perspectives[adapter_name] = text
                total_tokens += tokens
                tps = tokens / max((time.time() - start_time), 0.01)
                print(f"  [{adapter_name}] ({tokens} tok)")

            if len(perspectives) > 1:
                print(f"  [synthesizing...]")
                response = self.synthesize_perspectives(query, perspectives)
            else:
                response = list(perspectives.values())[0]

            elapsed = time.time() - start_time
            return {
                "response": response,
                "adapter": route.primary,
                "perspectives": perspectives,
                "adapters": list(perspectives.keys()),
                "route": route,
                "tokens": total_tokens,
                "time": elapsed,
                "tools_used": [],
                "confidence": route.confidence,
                "strategy": route.strategy,
                "memory_aware": self.memory_weighting is not None,
                "backend": "ollama",
            }

        # Single adapter
        response, tokens, tools = self.generate(
            query, adapter_name=route.primary, enable_tools=enable_tools
        )
        elapsed = time.time() - start_time

        return {
            "response": response,
            "adapter": route.primary,
            "route": route,
            "tokens": tokens,
            "time": elapsed,
            "tools_used": tools,
            "confidence": route.confidence,
            "strategy": route.strategy,
            "memory_aware": self.memory_weighting is not None,
            "backend": "ollama",
        }

    def synthesize_perspectives(self, query: str, perspectives: Dict[str, str]) -> str:
        """Synthesize multiple perspective responses into one — same as original."""
        max_per_perspective = max(200, (self.n_ctx - 1200) // max(len(perspectives), 1))
        max_chars = max_per_perspective * 4

        combined = "\n\n".join(
            f"**{name.upper()} PERSPECTIVE:**\n{text[:max_chars]}"
            for name, text in perspectives.items()
        )

        synthesis_prompt = f"""The user asked: "{query}"

Multiple perspectives have analyzed this:

{combined}

Your task: Synthesize these viewpoints into a single coherent response that:
1. Addresses the user's question directly
2. Integrates the strongest insights from each perspective
3. Arrives at a richer understanding than any single view

Synthesized response:"""

        result = self._chat([
            {"role": "system", "content": ADAPTER_PROMPTS["multi_perspective"]},
            {"role": "user", "content": synthesis_prompt},
        ])

        return result["content"]

    def set_memory_kernel(self, memory_kernel):
        """Attach a LivingMemoryKernel so cocoon knowledge enriches prompts."""
        self._memory_kernel = memory_kernel

    def _build_memory_context(self) -> str:
        """Build memory context string from cocoon memories."""
        if not hasattr(self, '_memory_kernel') or not self._memory_kernel:
            return ""
        try:
            memories = self._memory_kernel.recall(limit=3)
            if not memories:
                return ""
            lines = ["\n\n--- Cocoon Memory Context ---"]
            for mem in memories:
                emotion = getattr(mem, 'emotion', 'neutral')
                text = getattr(mem, 'text', str(mem))[:200]
                lines.append(f"[{emotion}] {text}")
            lines.append("--- End Memory ---\n")
            return "\n".join(lines)
        except Exception:
            return ""

    def log_routing_decision(self, route, query: str):
        """Log routing decision — same as original."""
        secondaries = ', '.join(route.secondary) if route.secondary else 'none'
        print(f"  Route: {route.primary} + {secondaries} "
              f"(conf={route.confidence:.2f}, {route.strategy})")
        if route.reasoning:
            print(f"  Reason: {route.reasoning}")

    def get_status(self) -> Dict:
        """Return orchestrator status for /api/status."""
        return {
            "backend": "ollama",
            "model": self._model_name,
            "ollama_url": OLLAMA_BASE_URL,
            "available_adapters": self.available_adapters,
            "n_ctx": self.n_ctx,
        }


# ================================================================
# CLI for testing
# ================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Codette Ollama Orchestrator")
    parser.add_argument("--query", "-q", type=str, help="Single query")
    parser.add_argument("--adapter", "-a", type=str, help="Force adapter")
    parser.add_argument("--model", "-m", type=str, help="Ollama model name")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.model:
        OLLAMA_MODEL = args.model

    orch = OllamaOrchestrator(verbose=args.verbose or True)

    if args.query:
        result = orch.route_and_generate(
            args.query, force_adapter=args.adapter
        )
        print(f"\n{result['response']}\n")
        print(f"[{result.get('adapter', 'base')} | {result.get('tokens', 0)} tokens | ollama]")
    else:
        # Interactive mode
        print("\nCodette (Ollama backend) — type 'quit' to exit\n")
        while True:
            try:
                query = input("You: ").strip()
                if query.lower() in ('quit', 'exit', 'q'):
                    break
                if not query:
                    continue
                result = orch.route_and_generate(query)
                adapter = result.get('adapter', 'base')
                print(f"\nCodette [{adapter}]: {result['response']}\n")
            except (KeyboardInterrupt, EOFError):
                break
        print("\nGoodbye!")
