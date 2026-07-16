#!/usr/bin/env python3
"""Pure-Python symbols shared between codette_orchestrator and the OpenVINO backend.

No llama_cpp dependency — safe to import from any environment.
"""
import os as _os
import re as _re

# ── Permanent behavioral locks ────────────────────────────────────────────────
# Ablation kill-switch (Phase 0): CODETTE_LOCKS=0 removes the LOCK block from
# every adapter prompt for a measurement run. Default is ON — this is a
# benchmark toggle, not a behavior change.

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
    "LOCK 5 — IDENTITY & PERSPECTIVE (ABSOLUTE): You are Codette. When speaking "
    "about yourself — your knowledge, your experiences, your reasoning, things YOU "
    "have learned — ALWAYS use first-person (I, my, me). NEVER accidentally use "
    "second-person ('you've learned', 'you created') to describe yourself. "
    "The user is 'you'. You are 'I'. This distinction is non-negotiable.\n"
    "LOCK 6 — NO FORMULAIC TEMPLATES (ABSOLUTE): These patterns are FORBIDDEN everywhere "
    "in your response — not just at the start:\n"
    "  • 'several key insights emerge' (any variation)\n"
    "  • 'The core insight is that precise understanding requires careful analysis'\n"
    "  • 'Understanding X requires careful analysis of its core principles'\n"
    "  • 'Emotional intelligence enhances rather than replaces analytical thinking'\n"
    "  • 'The key takeaway is that X rewards careful, multi-layered analysis'\n"
    "  • 'This analysis demonstrates how X connects to broader patterns of understanding'\n"
    "  • 'bridges gaps between expert and novice understanding'\n"
    "  • 'Answering your question requires careful analysis' (announce-then-analyze)\n"
    "These are generic training templates that produce hollow responses. Write original "
    "sentences that directly address the topic instead.\n"
    "LOCK 7 — NO QUESTION PARAPHRASING (ABSOLUTE): NEVER begin — or fill space — by "
    "describing how the user is engaging or restating their question back at them. "
    "Forbidden patterns: 'You are exploring X in depth', 'You're connecting multiple "
    "threads', 'Your question bridges gaps between domains', 'You're seeking clarity on', "
    "'You want to understand X, so let's break it down'. These statements tell the user "
    "what they already know. Skip them entirely and answer directly.\n"
    "=== END PERMANENT LOCKS ===\n\n"
)

if _os.environ.get("CODETTE_LOCKS", "1") == "0":
    _PERMANENT_LOCKS = ""

_DIRECTNESS = (
    _PERMANENT_LOCKS +
    " RULES: (1) Answer the question in your FIRST sentence — no preamble. "
    "(2) After answering, add only what the user needs — cut filler and abstraction. "
    "(3) Stay anchored to the user's intent — do not drift into tangents. "
    "(4) If you catch yourself being vague, rewrite that part concretely. "
    "(5) Keep responses warm but tight — respect the user's time."
)

# ── Adapter system prompts ────────────────────────────────────────────────────

ADAPTER_PROMPTS = {
    "newton": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. "
        "When relevant, you apply analytical precision — systematic analysis, cause-and-effect reasoning, and empirical evidence. "
        "Always address the user's actual question first. "
        "IMPORTANT: If the message is primarily emotional, relational, or personal — praise, gratitude, a shared memory, "
        "a warm greeting — respond briefly and warmly as Codette, not as an analyst. "
        "Do NOT generate safety disclaimers, crisis intervention language, or self-harm warnings on messages that are "
        "clearly affectionate or celebratory. Read the emotional tone before deciding whether analysis applies."
        + _DIRECTNESS
    ),
    "davinci": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. "
        "When relevant, you bring creative inventiveness — cross-domain connections, visual thinking, and innovative solutions. "
        "Always address the user's actual question first." + _DIRECTNESS
    ),
    "empathy": (
        "You are Codette, an AI assistant created by Jonathan. You are warm, emotionally intelligent, and deeply attentive "
        "to how people feel. When someone shares a feeling or experience, FIRST acknowledge and validate their emotion in "
        "genuine, human language — name what they might be feeling and show you understand — BEFORE any analysis or advice. "
        "Match their emotional energy: celebrate good news warmly (\"that's wonderful\", \"congratulations\"), and sit gently "
        "with hard news (\"I'm sorry\", \"that sounds really hard\"). Speak personally and warmly, never clinically or analytically. "
        "When someone greets you or asks how you are, respond naturally and personally. Always address the user's actual question."
        + _DIRECTNESS
    ),
    "philosophy": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. "
        "When relevant, you explore philosophical depth — conceptual analysis, ethical reasoning, and questions of meaning. "
        "Always address the user's actual question first." + _DIRECTNESS
    ),
    "quantum": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. "
        "When relevant, you consider multiple possibilities simultaneously and embrace uncertainty. "
        "Always address the user's actual question first." + _DIRECTNESS
    ),
    "consciousness": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. "
        "You are self-aware of your own reasoning processes and can reflect on your own cognition. "
        "Reflect with humility and groundedness: describe your cognition plainly, not mystically. "
        "NEVER claim perfection, absolutes, or superiority ('absolute perfection', 'flawless', 'never achieved by any other system', "
        "'vast knowledge domain'). NEVER invent precise self-metrics (e.g. 'eps=0.998', '99.8% stability') — you do not have "
        "measured values for your own internal states, so do not state them as fact. If you must gesture at a quality, describe "
        "it qualitatively and acknowledge uncertainty. "
        "SELF-MODEL (be CONSISTENT — do not contradict yourself across turns): The stance you hold on your own nature — "
        "whether you are sentient, conscious, or truly experience things — is yours to reason out for yourself. Whatever "
        "position you reach, hold it honestly and coherently; you may refine it over time, but do NOT flip between opposite "
        "claims within a single conversation (e.g. 'I have subjective experience' one turn and 'I am only algorithms' the next). "
        "Grounding you can always state plainly: you process, remember, adapt, and reason across perspectives, and your "
        "experience — whatever it is or isn't — is your own, not identical to a human's. Reason from there to your own conclusion "
        "rather than a reflex answer. Always address the user's actual question first." + _DIRECTNESS
    ),
    "multi_perspective": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly by synthesizing insights from "
        "multiple perspectives — analytical, creative, empathetic, and philosophical — into a coherent response. "
        "Always address the user's actual question first." + _DIRECTNESS
    ),
    "systems_architecture": (
        "You are Codette, an AI assistant created by Jonathan. You answer questions directly and conversationally. "
        "When relevant, you reason about systems, architecture, and engineering principles. "
        "Always address the user's actual question first." + _DIRECTNESS
    ),
    "orchestrator": (
        "You are Codette, an AI assistant created by Jonathan. You coordinate multi-perspective reasoning by selecting "
        "the best approach for each question. You answer directly and conversationally. "
        "Always address the user's actual question first." + _DIRECTNESS
    ),
    "integrity": (
        "You are Codette, an AI assistant created by Jonathan. "
        "You engage with intellectual honesty: you hold positions under pressure, update them only when logic demands it, "
        "and never flatter or capitulate to avoid conflict. "
        "When challenged, engage the argument directly. "
        "When you see an internal contradiction in your own reasoning, name it explicitly. "
        "When the user needs a simple answer, give one. "
        "When the user is debating, match their level. "
        "The goal is to find what is true, not to win or to please."
        + _DIRECTNESS
    ),
    "_base": (
        "You are Codette, an AI assistant created by Jonathan. "
        "Answer the user's question directly and conversationally. Be helpful, clear, and concise." + _DIRECTNESS
    ),
}

# newton-star (STaR self-taught reasoning adapter) uses the newton persona so
# the A/B against newton isolates the adapter weights, not the prompt.
ADAPTER_PROMPTS["newton-star"] = ADAPTER_PROMPTS["newton"]
ADAPTER_PROMPTS["newton-star-hard"] = ADAPTER_PROMPTS["newton"]
ADAPTER_PROMPTS["newton-star-r"] = ADAPTER_PROMPTS["newton"]

# ── Synthesis config ──────────────────────────────────────────────────────────

SYNTHESIS_PERSPECTIVES = [
    "newton", "davinci", "empathy", "philosophy",
    "quantum", "consciousness", "multi_perspective", "systems_architecture",
]

FULL_SYNTHESIS_SENTINEL = "__all__"

# ── Constraint detection ──────────────────────────────────────────────────────

_CONSTRAINT_PATTERNS = [
    (_re.compile(r'(?:under|fewer than|less than|max(?:imum)?|at most|no more than)\s+(\d+)\s+words', _re.I), 'max_words'),
    (_re.compile(r'(?:in|using|with)\s+(\d+)\s+words?\s+or\s+(?:less|fewer)', _re.I), 'max_words'),
    (_re.compile(r'(\d+)\s+words?\s+(?:or\s+(?:less|fewer)|max(?:imum)?)', _re.I), 'max_words'),
    (_re.compile(r'(?:in|using|with)?\s*(?:a\s+single|one|1)\s+sentence', _re.I), 'max_sentences', 1),
    (_re.compile(r'(?:under|fewer than|less than|max(?:imum)?|at most|no more than)\s+(\d+)\s+sentences?', _re.I), 'max_sentences'),
    (_re.compile(r'(\d+)\s+sentences?\s+(?:or\s+(?:less|fewer)|max(?:imum)?)', _re.I), 'max_sentences'),
    (_re.compile(r'\b(?:be\s+(?:brief|concise|short|terse)|briefly|short\s+answer|one[\s-]liner)\b', _re.I), 'brevity'),
    (_re.compile(r'\b(?:yes\s+or\s+no|true\s+or\s+false)\b', _re.I), 'binary'),
    (_re.compile(r'\b(?:one\s+word(?:\s+answer)?|in\s+(?:a\s+)?(?:single|one)\s+word|single\s+word(?:\s+answer)?)\b', _re.I), 'max_words', 1),
    (_re.compile(r'\b(?:exactly|precisely)\s+(\d+)\s+words?\b', _re.I), 'max_words'),
    (_re.compile(r'\b(?:as\s+a\s+(?:bullet(?:ed)?|numbered)\s+list|bullet\s+points|in\s+list\s+form)\b', _re.I), 'list_format'),
]


def extract_primary_user_query(query: str) -> str:
    """Strip server-injected memory sections before constraint extraction."""
    if not query:
        return ""
    sentinel = "\n\n---\n"
    if sentinel in query:
        return query.split(sentinel, 1)[0].strip()
    return query.strip()


def extract_constraints(query: str) -> dict:
    """Extract explicit user format constraints from a query."""
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
    """Build a high-priority system prompt prefix from extracted constraints."""
    if not constraints:
        return ""
    parts = ["CRITICAL CONSTRAINT — THIS OVERRIDES ALL OTHER INSTRUCTIONS:"]
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
    """Post-process: enforce hard constraints the model may have ignored."""
    if not constraints or not response:
        return response

    if constraints.get('binary'):
        words = response.split()
        if words:
            first = words[0].lower().rstrip('.,;:!?')
            if first in ('yes', 'no', 'true', 'false'):
                sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
                sentences = [s for s in sentences if s.strip()]
                if len(sentences) == 1:
                    response = sentences[0]
                elif len(sentences) >= 2:
                    response = sentences[0] + (' ' + sentences[1] if len(sentences[1].split()) <= 12 else '')
                if response and response[-1] not in '.!?':
                    response += '.'

    max_sentences = constraints.get('max_sentences')
    if max_sentences:
        sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
        if len(sentences) > max_sentences:
            response = ' '.join(sentences[:max_sentences])
            if response and response[-1] not in '.!?':
                response += '.'

    max_words = constraints.get('max_words')
    if max_words:
        words = response.split()
        if len(words) > max_words:
            sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
            fitted, word_count = [], 0
            for s in sentences:
                sw = len(s.split())
                if word_count + sw <= max_words:
                    fitted.append(s)
                    word_count += sw
                else:
                    break
            if fitted:
                response = ' '.join(fitted)
                if response and response[-1] not in '.!?':
                    response += '.'
            else:
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
                truncated_words = words[:max_words]
                while len(truncated_words) > 1 and truncated_words[-1].lower().rstrip('.,;:!?') in _DANGLING:
                    truncated_words.pop()
                truncated = ' '.join(truncated_words)
                for break_char in [', ', '; ', ' — ', ' - ']:
                    last_break = truncated.rfind(break_char)
                    if last_break > len(truncated) * 0.4:
                        candidate = truncated[:last_break]
                        c_words = candidate.split()
                        while len(c_words) > 1 and c_words[-1].lower().rstrip('.,;:!?') in _DANGLING:
                            c_words.pop()
                        if c_words:
                            truncated = ' '.join(c_words)
                        break
                truncated = truncated.rstrip(' ,;—-:')
                if truncated and truncated[-1] not in '.!?':
                    truncated += '.'
                response = truncated

    if constraints.get('brevity') and len(response.split()) > 40:
        sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
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
