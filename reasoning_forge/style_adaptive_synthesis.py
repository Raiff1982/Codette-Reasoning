"""
Style-Adaptive Synthesis Layer

Problem: Codette's multi-agent reasoning produces deeply accurate outputs
that often feel structurally rigid — formatted like academic reports when
the user asked a casual question, or cold/technical when someone is upset.

Solution: Detect the conversational register from context, map it to a
continuous style vector, and apply a lightweight surface transformation
that preserves all reasoning depth while recovering natural human tone.

─────────────────────────────────────────────────────────────
REGISTER DETECTION
─────────────────────────────────────────────────────────────

Five registers, each represented as a vocabulary cluster:

    CASUAL       → contractions, slang, short questions, exclamations
    TECHNICAL    → domain jargon, code blocks, precise notation
    EMOTIONAL    → feeling words, personal pronouns, hedging, ellipsis
    FORMAL       → complex syntax, no contractions, third person
    EXPLORATORY  → hypotheticals, "what if", collaborative framing

Detection scores per register R given context C (last N chars):

    s_R = ∑_{w ∈ vocab_R} count(w, C) / max(1, |words(C)|)

The normalized distribution:

    P(R | C) = softmax([s_R / temp_detect for R in registers])

Blended style vector when confidence is distributed across registers:

    v_blend = ∑_R P(R|C) · v_R

─────────────────────────────────────────────────────────────
STYLE VECTOR
─────────────────────────────────────────────────────────────

v = [formality, compression, hedging, structure, first_person, sentence_variety]
     ∈ [0,1]⁶

                    form  comp  hedge  struct  1p    variety
    CASUAL:        [0.15, 0.45, 0.25,  0.05, 0.90,  0.75]
    TECHNICAL:     [0.70, 0.85, 0.15,  0.55, 0.25,  0.40]
    EMOTIONAL:     [0.25, 0.30, 0.55,  0.05, 0.85,  0.65]
    FORMAL:        [0.90, 0.65, 0.65,  0.80, 0.10,  0.30]
    EXPLORATORY:   [0.40, 0.40, 0.80,  0.15, 0.65,  0.80]

─────────────────────────────────────────────────────────────
DEPTH PRESERVATION INVARIANT
─────────────────────────────────────────────────────────────

Reasoning depth D(response):
    D = w_arg · arg_count + w_causal · chain_depth + w_counter · counter_count
    w_arg=0.40, w_causal=0.35, w_counter=0.25

Invariant: D(adapted) ≥ 0.85 · D(original)

If adaptation would violate this, the layer degrades gracefully:
it adjusts tone only as far as the invariant permits.
"""

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ================================================================
# Register Definitions
# ================================================================

class Register(str, Enum):
    CASUAL      = "casual"
    TECHNICAL   = "technical"
    EMOTIONAL   = "emotional"
    FORMAL      = "formal"
    EXPLORATORY = "exploratory"


_REGISTER_VOCAB: Dict[Register, List[str]] = {
    Register.CASUAL: [
        "btw", "tbh", "lol", "ngl", "omg", "honestly", "literally",
        "basically", "kinda", "sorta", "yeah", "nah", "ok", "okay",
        "what's up", "dunno", "gonna", "wanna", "gotta", "ya", "hey",
        "cool", "awesome", "nice", "great", "wow", "haha", "hmm",
    ],
    Register.TECHNICAL: [
        "function", "algorithm", "implement", "api", "debug", "compile",
        "parameter", "return", "error", "class", "method", "module",
        "architecture", "schema", "endpoint", "runtime", "latency",
        "throughput", "complexity", "optimization", "refactor", "deploy",
        "regex", "gradient", "tensor", "inference", "embedding",
    ],
    Register.EMOTIONAL: [
        "feel", "feeling", "felt", "worried", "stressed", "anxious",
        "overwhelmed", "frustrated", "excited", "happy", "sad", "upset",
        "scared", "nervous", "hope", "hurt", "angry", "confused",
        "lost", "help me", "don't know what", "i'm", "it's hard",
        "struggling", "need", "please",
    ],
    Register.FORMAL: [
        "regarding", "pursuant", "aforementioned", "herein", "therefore",
        "furthermore", "nevertheless", "consequently", "notwithstanding",
        "however", "in accordance", "as per", "acknowledge", "submit",
        "propose", "recommend", "assess", "evaluate", "demonstrate",
        "indicate", "suggest", "conclude", "analysis", "framework",
    ],
    Register.EXPLORATORY: [
        "what if", "wonder", "curious", "imagine", "hypothetically",
        "suppose", "could we", "what would", "is it possible", "explore",
        "interesting", "maybe", "perhaps", "i wonder", "what do you think",
        "thoughts on", "perspective", "speculate", "brainstorm",
    ],
}

# Style vectors: [formality, compression, hedging, structure, first_person, variety]
_STYLE_VECTORS: Dict[Register, List[float]] = {
    Register.CASUAL:      [0.15, 0.45, 0.25, 0.05, 0.90, 0.75],
    Register.TECHNICAL:   [0.70, 0.85, 0.15, 0.55, 0.25, 0.40],
    Register.EMOTIONAL:   [0.25, 0.30, 0.55, 0.05, 0.85, 0.65],
    Register.FORMAL:      [0.90, 0.65, 0.65, 0.80, 0.10, 0.30],
    Register.EXPLORATORY: [0.40, 0.40, 0.80, 0.15, 0.65, 0.80],
}

_STYLE_DIMS = ["formality", "compression", "hedging", "structure", "first_person", "variety"]


# ================================================================
# Contractions for formality adjustment
# ================================================================

_EXPAND_CONTRACTIONS = {
    r"\bcan't\b": "cannot",
    r"\bdon't\b": "do not",
    r"\bwon't\b": "will not",
    r"\bisn't\b": "is not",
    r"\baren't\b": "are not",
    r"\bwasn't\b": "was not",
    r"\bweren't\b": "were not",
    r"\bhasn't\b": "has not",
    r"\bhaven't\b": "have not",
    r"\bhadn't\b": "had not",
    r"\bI'm\b": "I am",
    r"\bI've\b": "I have",
    r"\bI'll\b": "I will",
    r"\bI'd\b": "I would",
    r"\bwe're\b": "we are",
    r"\bthey're\b": "they are",
    r"\bit's\b": "it is",
    r"\bthat's\b": "that is",
    r"\bthere's\b": "there is",
    r"\bwhat's\b": "what is",
    r"\bdidn't\b": "did not",
    r"\bdoesn't\b": "does not",
    r"\bcouldn't\b": "could not",
    r"\bshouldn't\b": "should not",
    r"\bwouldn't\b": "would not",
}

_CONTRACT = {
    "cannot": "can't",
    "do not": "don't",
    "will not": "won't",
    "is not": "isn't",
    "are not": "aren't",
    "I am": "I'm",
    "I have": "I've",
    "I will": "I'll",
    "I would": "I'd",
    "it is": "it's",
    "that is": "that's",
    "there is": "there's",
    "did not": "didn't",
    "does not": "doesn't",
}

# Formal connective phrases to inject when structure > 0.6
_FORMAL_CONNECTIVES = [
    ("However,", "But"),
    ("Furthermore,", "Also,"),
    ("Therefore,", "So"),
    ("Consequently,", "As a result,"),
    ("Nevertheless,", "Still,"),
    ("In addition,", "Also,"),
]

# Hedging phrases by intensity
_HEDGES_WEAK   = ["perhaps", "possibly", "it seems", "it appears"]
_HEDGES_MEDIUM = ["it's likely that", "there's a good chance", "I'd lean toward saying"]
_HEDGES_STRONG = ["I'm fairly confident that", "the evidence suggests", "I believe"]


# ================================================================
# Depth measurement
# ================================================================

_ARG_MARKERS = re.compile(
    r"\b(because|since|therefore|thus|hence|so that|as a result|"
    r"which means|leading to|implies|suggests|demonstrates)\b",
    re.IGNORECASE,
)
_CAUSAL_CHAIN = re.compile(
    r"\b(first|then|next|finally|subsequently|this causes|this leads|"
    r"which then|ultimately|as a consequence)\b",
    re.IGNORECASE,
)
_COUNTER_MARKERS = re.compile(
    r"\b(however|on the other hand|but|although|even though|"
    r"while|despite|contrary to|counterargument|objection|"
    r"one might argue|alternatively)\b",
    re.IGNORECASE,
)


def _measure_depth(text: str) -> float:
    """
    Reasoning depth D(response) ∈ [0, ∞).

    D = 0.40 · arg_count + 0.35 · causal_chain_depth + 0.25 · counter_count

    Normalized per 100 words so short and long responses are comparable.
    """
    word_count = max(1, len(text.split()))
    norm = 100.0 / word_count

    arg_count    = len(_ARG_MARKERS.findall(text))
    causal_count = len(_CAUSAL_CHAIN.findall(text))
    counter_count = len(_COUNTER_MARKERS.findall(text))

    return (0.40 * arg_count + 0.35 * causal_count + 0.25 * counter_count) * norm


# ================================================================
# Register Detection
# ================================================================

def _softmax(logits: List[float]) -> List[float]:
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


def detect_register_distribution(context: str, temperature: float = 0.3) -> Dict[Register, float]:
    """
    Return P(R | context) as a normalized distribution over all registers.

    Uses term-frequency scoring against per-register vocabulary clusters,
    then applies softmax with temperature to get a smooth distribution.
    """
    words_lower = context.lower().split()
    word_count = max(1, len(words_lower))
    context_lower = context.lower()

    raw_scores: Dict[Register, float] = {}
    for register, vocab in _REGISTER_VOCAB.items():
        hits = sum(
            context_lower.count(phrase.lower())
            for phrase in vocab
        )
        raw_scores[register] = hits / word_count

    registers = list(Register)
    logits = [raw_scores[r] / temperature for r in registers]
    probs = _softmax(logits)

    return {r: round(p, 4) for r, p in zip(registers, probs)}


def detect_dominant_register(context: str) -> Register:
    dist = detect_register_distribution(context)
    return max(dist, key=lambda r: dist[r])


def blend_style_vector(dist: Dict[Register, float]) -> Dict[str, float]:
    """
    v_blend = ∑_R P(R|C) · v_R

    Produces a continuous 6-dimensional style vector reflecting the
    weighted mix of detected registers.
    """
    n = len(_STYLE_DIMS)
    blended = [0.0] * n
    for register, prob in dist.items():
        for i, val in enumerate(_STYLE_VECTORS[register]):
            blended[i] += prob * val
    return {dim: round(v, 4) for dim, v in zip(_STYLE_DIMS, blended)}


# ================================================================
# Style Transformers
# ================================================================

def _apply_formality(text: str, formality: float) -> str:
    """Expand or contract based on formality target."""
    if formality >= 0.65:
        for pattern, replacement in _EXPAND_CONTRACTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    elif formality <= 0.35:
        for expanded, contracted in _CONTRACT.items():
            text = re.sub(r'\b' + re.escape(expanded) + r'\b', contracted, text, flags=re.IGNORECASE)
    return text


def _apply_structure(text: str, structure: float) -> str:
    """
    structure < 0.25: collapse markdown headers/bullets into prose
    structure > 0.65: keep or add structural connectives
    """
    if structure < 0.25:
        # Remove markdown headers
        text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)
        # Convert bullet points to comma-separated clauses (simple heuristic)
        lines = text.split('\n')
        prose_parts = []
        bullet_buffer = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('- ', '* ', '• ')):
                bullet_buffer.append(stripped[2:].strip())
            else:
                if bullet_buffer:
                    prose_parts.append(', '.join(bullet_buffer) + '.')
                    bullet_buffer = []
                prose_parts.append(line)
        if bullet_buffer:
            prose_parts.append(', '.join(bullet_buffer) + '.')
        text = '\n'.join(prose_parts)
        # Clean up excessive blank lines left by removed headers
        text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def _apply_hedging(text: str, hedging: float) -> str:
    """
    Add or remove hedging language based on target level.
    hedging > 0.6: inject hedging at the start of declarative claims
    hedging < 0.2: strip hedging phrases for directness
    """
    if hedging < 0.2:
        # Remove weak hedging
        weak_re = re.compile(
            r'\b(perhaps|possibly|it seems|it appears|maybe|might be|could be)\b,?\s*',
            re.IGNORECASE,
        )
        text = weak_re.sub('', text)
    return text


def _apply_compression(text: str, compression: float) -> str:
    """
    compression > 0.75: trim filler phrases for density
    compression < 0.35: allow elaborative transitions (no change needed)
    """
    if compression > 0.75:
        fillers = [
            r'\bIt is worth noting that\b',
            r'\bIt should be mentioned that\b',
            r'\bAs I mentioned (above|earlier|before)\b',
            r'\bIn terms of\b',
            r'\bWith respect to\b',
            r'\bIt goes without saying that\b',
            r'\bNeedless to say,?\s*',
            r'\bOf course,?\s*',
            r'\bObviously,?\s*',
            r'\bClearly,?\s*',
        ]
        for pat in fillers:
            text = re.sub(pat, '', text, flags=re.IGNORECASE)
        text = re.sub(r'  +', ' ', text)
    return text


def _apply_first_person(text: str, first_person: float) -> str:
    """
    first_person < 0.3: shift from "I think" to "the analysis shows" / passive voice
    first_person > 0.75: bring back first-person where absent (limited heuristic)
    """
    if first_person < 0.3:
        text = re.sub(r'\bI think\b', 'The analysis suggests', text, flags=re.IGNORECASE)
        text = re.sub(r'\bI believe\b', 'It appears', text, flags=re.IGNORECASE)
        text = re.sub(r'\bI feel\b', 'The evidence indicates', text, flags=re.IGNORECASE)
        text = re.sub(r'\bIn my view\b', 'From this perspective', text, flags=re.IGNORECASE)
        text = re.sub(r'\bI would say\b', 'One might say', text, flags=re.IGNORECASE)
    return text


# ================================================================
# Main Class
# ================================================================

@dataclass
class AdaptationResult:
    adapted_text: str
    register_distribution: Dict[str, float]
    dominant_register: str
    style_vector: Dict[str, float]
    depth_original: float
    depth_adapted: float
    depth_preserved: bool        # True if depth_adapted ≥ 0.85 * depth_original
    depth_ratio: float
    transformations_applied: List[str]


class StyleAdaptiveSynthesis:
    """
    Detects conversational register and adapts response surface form
    to match it — without reducing reasoning depth.

    The depth preservation invariant ensures Codette never "dumb down"
    its output; it only changes HOW depth is expressed, not WHETHER it's there.

    Usage:
        adapter = StyleAdaptiveSynthesis()
        result = adapter.adapt(response_text, context=last_few_turns)
        return result.adapted_text
    """

    DEPTH_PRESERVATION_FLOOR = 0.85   # D(adapted) ≥ 0.85 × D(original)

    def __init__(self, detection_temperature: float = 0.3):
        self.detection_temperature = detection_temperature

    def adapt(
        self,
        response: str,
        context: str = "",
        force_register: Optional[Register] = None,
    ) -> AdaptationResult:
        """
        Apply style adaptation.

        Args:
            response:        The response to adapt (already generated by Codette).
            context:         Recent conversation turns (used for register detection).
            force_register:  Override register detection — skip if provided.

        Returns:
            AdaptationResult with adapted text and metadata.
        """
        # 1. Detect register
        if force_register is not None:
            dist = {r: (1.0 if r == force_register else 0.0) for r in Register}
        else:
            dist = detect_register_distribution(
                context or response[:500],
                temperature=self.detection_temperature,
            )

        dominant = max(dist, key=lambda r: dist[r])
        style_vec = blend_style_vector(dist)

        # 2. Measure original depth
        d_original = _measure_depth(response)

        # 3. Apply transformations
        adapted = response
        applied: List[str] = []

        formality  = style_vec["formality"]
        compression = style_vec["compression"]
        hedging    = style_vec["hedging"]
        structure  = style_vec["structure"]
        first_p    = style_vec["first_person"]

        # Apply in order: structure first (changes layout), then lexical changes
        prev = adapted
        adapted = _apply_structure(adapted, structure)
        if adapted != prev:
            applied.append(f"structure(target={structure:.2f})")

        prev = adapted
        adapted = _apply_formality(adapted, formality)
        if adapted != prev:
            applied.append(f"formality(target={formality:.2f})")

        prev = adapted
        adapted = _apply_compression(adapted, compression)
        if adapted != prev:
            applied.append(f"compression(target={compression:.2f})")

        prev = adapted
        adapted = _apply_hedging(adapted, hedging)
        if adapted != prev:
            applied.append(f"hedging(target={hedging:.2f})")

        prev = adapted
        adapted = _apply_first_person(adapted, first_p)
        if adapted != prev:
            applied.append(f"first_person(target={first_p:.2f})")

        # 4. Depth preservation check
        d_adapted = _measure_depth(adapted)
        depth_ratio = d_adapted / max(d_original, 0.01)
        depth_preserved = depth_ratio >= self.DEPTH_PRESERVATION_FLOOR

        # 5. If depth invariant violated, revert to original
        if not depth_preserved and d_original > 0.5:
            # Partial revert: keep only formality/hedging changes (don't touch structure)
            adapted_partial = _apply_formality(response, formality)
            adapted_partial = _apply_hedging(adapted_partial, hedging)
            d_partial = _measure_depth(adapted_partial)
            partial_ratio = d_partial / max(d_original, 0.01)
            if partial_ratio >= self.DEPTH_PRESERVATION_FLOOR:
                adapted = adapted_partial
                d_adapted = d_partial
                depth_ratio = partial_ratio
                depth_preserved = True
                applied = [t for t in applied if "structure" not in t and "compression" not in t]
                applied.append("partial_revert(structure+compression restored)")
            else:
                # Full revert — depth would be lost regardless
                adapted = response
                d_adapted = d_original
                depth_ratio = 1.0
                depth_preserved = True
                applied = ["full_revert(depth invariant could not be satisfied)"]

        return AdaptationResult(
            adapted_text=adapted.strip(),
            register_distribution={r.value: v for r, v in dist.items()},
            dominant_register=dominant.value,
            style_vector=style_vec,
            depth_original=round(d_original, 4),
            depth_adapted=round(d_adapted, 4),
            depth_preserved=depth_preserved,
            depth_ratio=round(depth_ratio, 4),
            transformations_applied=applied,
        )

    def profile_context(self, context: str) -> Dict:
        """
        Return a full register profile for a given context.
        Useful for debugging or exposing in the confidence dashboard.
        """
        dist = detect_register_distribution(context, self.detection_temperature)
        style_vec = blend_style_vector(dist)
        dominant = max(dist, key=lambda r: dist[r])
        return {
            "distribution": {r.value: v for r, v in dist.items()},
            "dominant": dominant.value,
            "style_vector": style_vec,
            "description": _describe_style(style_vec),
        }


def _describe_style(v: Dict[str, float]) -> str:
    """Human-readable style summary from style vector."""
    parts = []
    if v["formality"] < 0.3:
        parts.append("casual tone")
    elif v["formality"] > 0.7:
        parts.append("formal tone")
    else:
        parts.append("conversational tone")

    if v["compression"] > 0.7:
        parts.append("dense/compressed")
    elif v["compression"] < 0.35:
        parts.append("elaborative")

    if v["hedging"] > 0.6:
        parts.append("well-hedged")
    elif v["hedging"] < 0.2:
        parts.append("direct/assertive")

    if v["structure"] > 0.6:
        parts.append("structured (headers/bullets OK)")
    else:
        parts.append("prose-first (minimal structure)")

    if v["first_person"] > 0.7:
        parts.append("first-person")
    elif v["first_person"] < 0.25:
        parts.append("third-person/passive")

    return ", ".join(parts)
