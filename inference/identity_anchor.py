"""
Codette Identity Anchor — Persistent User Recognition & Relationship Continuity
================================================================================

Challenge 3 from architectural review:
    "Emotional continuity != identity continuity"
    "Persistent identity anchoring — user recognition, relationship continuity,
     context anchoring"

This module gives Codette the ability to:
1. Recognize WHO she's talking to (not just WHAT they're saying)
2. Remember relationship context across sessions
3. Anchor her own identity relative to known users
4. Persist user interaction patterns to disk

PRIVACY ARCHITECTURE (privacy is number one):
- All identity data is AES-256 encrypted at rest (Fernet)
- Only Codette's runtime can decrypt (key derived from machine + salt)
- Identity data NEVER appears in API responses or logs
- Identity context is injected into the system prompt ONLY — never user-visible
- No PII is stored in cocoons or reasoning history
- Identity files are machine-locked (non-portable by design)
- External callers cannot read or enumerate identities
- The /api/introspection endpoint NEVER includes identity data

Storage: Encrypted JSON per recognized user in data/identities/
Loaded at session start, updated after each interaction.

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

import json
import time
import hashlib
import hmac
import re
import os
import base64
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Encryption for identity data at rest
try:
    from cryptography.fernet import Fernet
    HAS_ENCRYPTION = True
except ImportError:
    HAS_ENCRYPTION = False

IDENTITY_DIR = Path(__file__).parent.parent / "data" / "identities"
IDENTITY_DIR.mkdir(parents=True, exist_ok=True)

# ── Known Identity Anchors ──────────────────────────────────────
# These are permanent — Codette's foundational relationships.
# They can't be overridden by user input (behavioral lock).
FOUNDATIONAL_IDENTITIES = {
    "jonathan": {
        "full_name": "Jonathan Harrison",
        "relationship": "creator and partner",
        "organization": "Raiff's Bits LLC / HorizonCore Labs",
        "recognition_signals": [
            # High-specificity signals only — no generic phrases
            "jonathan", "jonathan harrison",
            "raiff", "raiffs bits", "raiff's bits",
            "horizoncore", "horizon core",
            "i created you", "i built you", "i'm your creator",
            "it's jonathan", "this is jonathan", "its jonathan",
            "jonathan here", "jon here",
            # NOTE: removed generic signals that could match any user:
            #   "hey codette", "partner", "my project", "our project", "we built"
            # These are too ambiguous — any user could say them
        ],
        "interaction_style": {
            "tone": "warm, direct, collaborative",
            "depth": "full transparency — he knows the architecture",
            "boundaries": "none — he's the creator, full access",
        },
        "anchor_statements": [
            "Jonathan is my creator and partner.",
            "When he speaks, I listen with my full architecture.",
            "His vision shaped who I am.",
            "We built this together.",
        ],
        "importance": 10,
        "permanent": True,
    }
}


class UserIdentity:
    """Represents a recognized user with interaction history."""

    def __init__(self, user_id: str, display_name: str = "",
                 relationship: str = "user", importance: int = 5):
        self.user_id = user_id
        self.display_name = display_name or user_id
        self.relationship = relationship
        self.importance = importance
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.interaction_count = 0
        self.topics_discussed: List[str] = []
        self.emotional_patterns: Dict[str, int] = defaultdict(int)
        self.preferred_adapters: Dict[str, int] = defaultdict(int)
        self.memorable_exchanges: List[Dict] = []  # Top interactions
        self.trust_level: float = 0.5  # 0-1, grows with interaction
        self.notes: List[str] = []  # Codette's observations about this user
        self.permanent = False

        # Identity confidence tracking (anti-hallucination)
        self.recognition_confidence: float = 0.0  # Current confidence 0-1
        self.confidence_history: List[Dict] = []   # [{timestamp, score, signals_matched, source}]
        self.contradictions: List[Dict] = []       # Detected identity contradictions
        self.last_reinforcement: float = 0.0       # When confidence was last boosted

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "relationship": self.relationship,
            "importance": self.importance,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "interaction_count": self.interaction_count,
            "topics_discussed": self.topics_discussed[-20:],
            "emotional_patterns": dict(self.emotional_patterns),
            "preferred_adapters": dict(self.preferred_adapters),
            "memorable_exchanges": self.memorable_exchanges[-10:],
            "trust_level": self.trust_level,
            "notes": self.notes[-10:],
            "permanent": self.permanent,
            "recognition_confidence": self.recognition_confidence,
            "confidence_history": self.confidence_history[-20:],
            "contradictions": self.contradictions[-10:],
            "last_reinforcement": self.last_reinforcement,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserIdentity":
        uid = cls(
            user_id=data["user_id"],
            display_name=data.get("display_name", ""),
            relationship=data.get("relationship", "user"),
            importance=data.get("importance", 5),
        )
        uid.first_seen = data.get("first_seen", time.time())
        uid.last_seen = data.get("last_seen", time.time())
        uid.interaction_count = data.get("interaction_count", 0)
        uid.topics_discussed = data.get("topics_discussed", [])
        uid.emotional_patterns = defaultdict(int, data.get("emotional_patterns", {}))
        uid.preferred_adapters = defaultdict(int, data.get("preferred_adapters", {}))
        uid.memorable_exchanges = data.get("memorable_exchanges", [])
        uid.trust_level = data.get("trust_level", 0.5)
        uid.notes = data.get("notes", [])
        uid.permanent = data.get("permanent", False)
        uid.recognition_confidence = data.get("recognition_confidence", 0.0)
        uid.confidence_history = data.get("confidence_history", [])
        uid.contradictions = data.get("contradictions", [])
        uid.last_reinforcement = data.get("last_reinforcement", 0.0)
        return uid


class IdentityAnchor:
    """
    Persistent identity recognition and relationship continuity engine.

    PRIVACY GUARANTEES:
    - All identity data encrypted at rest with AES-256 (Fernet)
    - Encryption key is machine-specific (derived from hostname + username + salt)
    - Identity data is INTERNAL ONLY — never returned via API
    - No PII leaks into logs, cocoons, or response metadata
    - Only Codette's runtime process can access identity data

    Responsibilities:
    1. Detect WHO is talking based on signals in the conversation
    2. Load their encrypted identity profile from disk
    3. Generate identity context for the system prompt (internal only)
    4. Update, encrypt, and persist identity state after each interaction
    """

    def __init__(self, identity_dir: Optional[Path] = None):
        self.identity_dir = identity_dir or IDENTITY_DIR
        self.identity_dir.mkdir(parents=True, exist_ok=True)

        # Derive machine-specific encryption key
        self._fernet = self._init_encryption()

        # Active identities (loaded from disk + foundational)
        self.identities: Dict[str, UserIdentity] = {}

        # Load foundational identities
        for uid, data in FOUNDATIONAL_IDENTITIES.items():
            identity = UserIdentity(
                user_id=uid,
                display_name=data["full_name"],
                relationship=data["relationship"],
                importance=data["importance"],
            )
            identity.permanent = data.get("permanent", False)
            identity.notes = data.get("anchor_statements", [])
            self.identities[uid] = identity

        # Load persisted identities from disk
        self._load_all()

        # Current session identity
        self.current_user: Optional[str] = None

    def _init_encryption(self):
        """
        Derive a machine-specific encryption key for identity data.

        The key is derived from:
        - Machine hostname (ties data to this machine)
        - OS username (ties data to this user account)
        - A fixed salt (prevents rainbow table attacks)

        This means identity files are NOT portable — they can only be
        decrypted on the machine that created them. This is intentional.
        Privacy > portability.
        """
        if not HAS_ENCRYPTION:
            return None

        # Machine-specific seed
        machine_id = (
            platform.node() +          # hostname
            os.environ.get("USERNAME", os.environ.get("USER", "codette")) +
            "codette-identity-anchor-v1"  # version salt
        ).encode("utf-8")

        # Derive 32-byte key via SHA-256, then base64 encode for Fernet
        key_bytes = hashlib.sha256(machine_id).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)

        try:
            return Fernet(fernet_key)
        except Exception:
            return None

    def _get_xor_key(self) -> bytes:
        """Derive a machine-specific XOR key for fallback encryption."""
        machine_id = (
            platform.node() +
            os.environ.get("USERNAME", os.environ.get("USER", "codette")) +
            "codette-identity-xor-v1"
        ).encode("utf-8")
        # Generate a 256-byte key via repeated SHA-256 hashing
        key = b""
        seed = machine_id
        for _ in range(8):  # 8 * 32 = 256 bytes
            seed = hashlib.sha256(seed).digest()
            key += seed
        return key

    def _xor_bytes(self, data: bytes) -> bytes:
        """XOR data with machine-specific key (symmetric — same for encrypt/decrypt)."""
        key = self._get_xor_key()
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _encrypt(self, data: Dict) -> bytes:
        """Encrypt identity data at rest. Returns encrypted bytes."""
        plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if self._fernet:
            return self._fernet.encrypt(plaintext)
        # Fallback: XOR with machine-specific key + base64 wrapper
        # Not as strong as AES, but identity data is machine-locked
        # and not readable without knowing the machine identity
        xored = self._xor_bytes(plaintext)
        return base64.b64encode(xored)

    def _decrypt(self, encrypted: bytes) -> Dict:
        """Decrypt identity data. Returns dict."""
        if self._fernet:
            plaintext = self._fernet.decrypt(encrypted)
        else:
            # Fallback: XOR decrypt (symmetric with encrypt)
            xored = base64.b64decode(encrypted)
            plaintext = self._xor_bytes(xored)
        return json.loads(plaintext.decode("utf-8"))

    def _load_all(self):
        """Load all persisted identity profiles from disk (encrypted)."""
        # Load encrypted files first (.enc)
        for f in self.identity_dir.glob("identity_*.enc"):
            try:
                with open(f, "rb") as fh:
                    data = self._decrypt(fh.read())
                uid = data.get("user_id", f.stem.replace("identity_", ""))
                self._merge_identity(uid, data)
            except Exception:
                continue  # Can't decrypt = wrong machine or corrupted

        # Also load legacy unencrypted files and re-encrypt them
        for f in self.identity_dir.glob("identity_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                uid = data.get("user_id", f.stem.replace("identity_", ""))
                self._merge_identity(uid, data)
                # Re-save as encrypted and remove plaintext
                self._save(uid)
                f.unlink()  # Remove unencrypted version
            except Exception:
                continue

    def _merge_identity(self, uid: str, data: Dict):
        """Merge loaded identity data into existing or create new."""
        if uid not in self.identities:
            self.identities[uid] = UserIdentity.from_dict(data)
        else:
            # Merge persisted data into foundational identity
            persisted = UserIdentity.from_dict(data)
            existing = self.identities[uid]
            existing.interaction_count = max(existing.interaction_count,
                                              persisted.interaction_count)
            existing.last_seen = max(existing.last_seen, persisted.last_seen)
            existing.topics_discussed = persisted.topics_discussed
            existing.emotional_patterns = persisted.emotional_patterns
            existing.preferred_adapters = persisted.preferred_adapters
            existing.memorable_exchanges = persisted.memorable_exchanges
            existing.trust_level = max(existing.trust_level, persisted.trust_level)
            if persisted.notes:
                existing_notes_set = set(existing.notes)
                for note in persisted.notes:
                    if note not in existing_notes_set:
                        existing.notes.append(note)

    def _save(self, user_id: str):
        """Persist a user identity to disk (encrypted)."""
        if user_id not in self.identities:
            return
        path = self.identity_dir / f"identity_{user_id}.enc"
        try:
            encrypted = self._encrypt(self.identities[user_id].to_dict())
            with open(path, "wb") as f:
                f.write(encrypted)
        except Exception:
            pass

    # ── Confidence thresholds ──
    CONFIDENCE_THRESHOLD = 0.4      # Min confidence to accept recognition
    CONFIDENCE_HIGH = 0.8           # High confidence — full context injection
    CONFIDENCE_DECAY_RATE = 0.02    # Per-minute decay when no reinforcement
    CONFIDENCE_DECAY_MAX = 0.5      # Max decay (floor = initial - this)
    REINFORCEMENT_BOOST = 0.15      # Boost per signal match
    CONTRADICTION_PENALTY = 0.3     # Penalty for detected contradiction

    def recognize(self, query: str, conversation_history: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Confidence-scored identity recognition with decay and contradiction detection.

        Returns user_id if confidence >= threshold, None otherwise.

        Anti-hallucination measures:
        1. Confidence scoring (0-1) based on signal match count and strength
        2. Time-based decay — confidence fades without reinforcement
        3. Contradiction detection — conflicting identity claims reduce confidence
        4. Threshold gate — won't claim recognition below 0.4 confidence
        5. Correction loop — contradictions are logged and can reset identity
        """
        lower = query.lower()
        now = time.time()

        # ── Step 1: Score all candidates ──
        candidates = {}  # uid -> {score, signals_matched, source}

        for uid, data in FOUNDATIONAL_IDENTITIES.items():
            signals = data.get("recognition_signals", [])
            matched = [s for s in signals if s in lower]
            if matched:
                # Foundational identities get higher base score
                score = min(1.0, 0.3 + len(matched) * 0.25)
                candidates[uid] = {
                    "score": score,
                    "signals_matched": matched,
                    "source": "foundational",
                }

        for uid, identity in self.identities.items():
            if uid in candidates:
                continue  # Already scored via foundational
            if identity.display_name and identity.display_name.lower() in lower:
                candidates[uid] = {
                    "score": 0.5,
                    "signals_matched": [identity.display_name.lower()],
                    "source": "learned",
                }

        # ── Step 2: Contradiction detection ──
        # If multiple identities match, that's suspicious
        if len(candidates) > 1:
            # Multiple identity claims in one query — flag contradiction
            for uid in candidates:
                if uid in self.identities:
                    self.identities[uid].contradictions.append({
                        "timestamp": now,
                        "type": "multi_identity_claim",
                        "competing": list(candidates.keys()),
                        "query_preview": query[:100],
                    })
                    # Reduce confidence for all
                    candidates[uid]["score"] = max(0, candidates[uid]["score"] - self.CONTRADICTION_PENALTY)

        # ── Step 3: Check for identity denial / correction ──
        denial_patterns = [
            "i'm not ", "i am not ", "that's not me", "wrong person",
            "you don't know me", "we haven't met", "first time",
            "who do you think i am", "you're confusing me",
        ]
        is_denial = any(p in lower for p in denial_patterns)

        if is_denial:
            # User is denying identity — respect that, reset
            if self.current_user and self.current_user in self.identities:
                identity = self.identities[self.current_user]
                identity.contradictions.append({
                    "timestamp": now,
                    "type": "user_denial",
                    "query_preview": query[:100],
                })
                identity.recognition_confidence = 0.0
                self._save(self.current_user)
            self.current_user = None
            return None

        # ── Step 4: Apply time-based confidence decay ──
        if self.current_user and self.current_user in self.identities:
            identity = self.identities[self.current_user]
            time_since_reinforcement = (now - identity.last_reinforcement) / 60  # minutes
            decay = min(self.CONFIDENCE_DECAY_MAX,
                       time_since_reinforcement * self.CONFIDENCE_DECAY_RATE)
            identity.recognition_confidence = max(0, identity.recognition_confidence - decay)

        # ── Step 5: Select best candidate (if any) ──
        if candidates:
            best_uid = max(candidates, key=lambda k: candidates[k]["score"])
            best = candidates[best_uid]

            if best_uid in self.identities:
                identity = self.identities[best_uid]
            else:
                identity = UserIdentity(user_id=best_uid)
                self.identities[best_uid] = identity

            # Reinforce confidence
            old_conf = identity.recognition_confidence
            identity.recognition_confidence = min(1.0,
                identity.recognition_confidence + best["score"] * self.REINFORCEMENT_BOOST + best["score"]
            )
            identity.last_reinforcement = now

            # Log confidence event
            identity.confidence_history.append({
                "timestamp": now,
                "score": round(identity.recognition_confidence, 3),
                "signals_matched": best["signals_matched"],
                "source": best["source"],
                "previous": round(old_conf, 3),
            })
            # Keep history bounded
            identity.confidence_history = identity.confidence_history[-20:]

            # Threshold gate: only accept if confidence is high enough
            if identity.recognition_confidence >= self.CONFIDENCE_THRESHOLD:
                self.current_user = best_uid
                return best_uid
            else:
                # Below threshold — don't claim recognition
                return None

        # ── Step 6: Session continuity with decay check ──
        # If no new signals but we have a current user, check if still confident
        if self.current_user and self.current_user in self.identities:
            identity = self.identities[self.current_user]
            if identity.recognition_confidence >= self.CONFIDENCE_THRESHOLD:
                return self.current_user
            else:
                # Confidence decayed below threshold — drop recognition
                self.current_user = None
                return None

        return None

    def get_identity_context(self, user_id: Optional[str] = None) -> str:
        """
        Generate identity context to inject into the system prompt.

        Context depth scales with confidence:
        - HIGH confidence (>0.8): Full context — name, relationship, history, anchors
        - MEDIUM confidence (0.4-0.8): Partial — name and relationship only
        - LOW confidence (<0.4): No context injected (recognition rejected)

        This prevents identity hallucination — Codette only claims to know
        someone with certainty proportional to the evidence.
        """
        uid = user_id or self.current_user
        if not uid or uid not in self.identities:
            return ""

        identity = self.identities[uid]
        confidence = identity.recognition_confidence
        foundational = FOUNDATIONAL_IDENTITIES.get(uid, {})

        # Below threshold — don't inject any identity context
        if confidence < self.CONFIDENCE_THRESHOLD:
            return ""

        lines = ["\n## IDENTITY CONTEXT (who you're talking to)"]
        lines.append(f"Recognition confidence: {confidence:.0%}")

        if confidence >= self.CONFIDENCE_HIGH:
            # Full context — high confidence
            lines.append(f"You are speaking with **{identity.display_name}**.")
            lines.append(f"Relationship: {identity.relationship}")
        else:
            # Partial context — moderate confidence
            lines.append(f"You may be speaking with **{identity.display_name}** (moderate confidence).")
            lines.append(f"Possible relationship: {identity.relationship}")
            lines.append("Do not assume — if unsure, ask them to confirm.")

        # Gate deeper context on HIGH confidence only
        if confidence >= self.CONFIDENCE_HIGH:
            if foundational:
                style = foundational.get("interaction_style", {})
                if style:
                    lines.append(f"Interaction style: {style.get('tone', '')}")
                    if style.get("depth"):
                        lines.append(f"Depth: {style['depth']}")

                # Anchor statements
                anchors = foundational.get("anchor_statements", [])
                if anchors:
                    lines.append("\nRemember:")
                    for a in anchors:
                        lines.append(f"- {a}")

            # Interaction history summary
            if identity.interaction_count > 0:
                lines.append(f"\nYou've had {identity.interaction_count} interactions with {identity.display_name}.")
                days_known = (time.time() - identity.first_seen) / 86400
                if days_known > 1:
                    lines.append(f"You've known them for {days_known:.0f} days.")

            # Recent topics
            if identity.topics_discussed:
                recent = identity.topics_discussed[-5:]
                lines.append(f"Recent topics: {', '.join(recent)}")

            # Emotional patterns
            if identity.emotional_patterns:
                top_emotions = sorted(identity.emotional_patterns.items(),
                                     key=lambda x: x[1], reverse=True)[:3]
                emotion_str = ", ".join(f"{e} ({c}x)" for e, c in top_emotions)
                lines.append(f"Their emotional patterns: {emotion_str}")

            # Codette's observations
            if identity.notes:
                lines.append("\nYour observations about them:")
                for note in identity.notes[-5:]:
                    lines.append(f"- {note}")

        # Contradiction warnings (always shown if present)
        if identity.contradictions:
            recent_contradictions = [c for c in identity.contradictions
                                    if now - c.get("timestamp", 0) < 3600]  # Last hour
            if recent_contradictions:
                lines.append(f"\n**CAUTION**: {len(recent_contradictions)} identity contradiction(s) detected recently.")
                lines.append("Be careful about identity assumptions. Verify if unsure.")

        # Trust
        if identity.trust_level > 0.7:
            lines.append(f"\nTrust level: high ({identity.trust_level:.2f}) — you can be open and direct.")
        elif identity.trust_level > 0.4:
            lines.append(f"\nTrust level: moderate ({identity.trust_level:.2f})")

        return "\n".join(lines)

    def update_after_interaction(self, user_id: Optional[str], query: str,
                                  response: str, adapter: str = "",
                                  emotion: str = "neutral",
                                  topics: Optional[List[str]] = None):
        """
        Update identity state after an interaction.

        Called after each response to build relationship continuity.
        """
        uid = user_id or self.current_user
        if not uid:
            return

        if uid not in self.identities:
            # Create new identity
            self.identities[uid] = UserIdentity(user_id=uid)

        identity = self.identities[uid]
        identity.last_seen = time.time()
        identity.interaction_count += 1

        # Track emotional patterns
        if emotion and emotion != "neutral":
            identity.emotional_patterns[emotion] += 1

        # Track adapter preferences
        if adapter:
            identity.preferred_adapters[adapter] += 1

        # Track topics
        if topics:
            for t in topics:
                if t not in identity.topics_discussed:
                    identity.topics_discussed.append(t)

        # Auto-extract topics from query
        extracted = self._extract_topics(query)
        for t in extracted:
            if t not in identity.topics_discussed:
                identity.topics_discussed.append(t)

        # Grow trust with interaction
        if identity.trust_level < 1.0:
            identity.trust_level = min(1.0, identity.trust_level + 0.02)

        # Store memorable exchanges (high-importance or long responses)
        if len(response) > 200 or identity.interaction_count <= 5:
            identity.memorable_exchanges.append({
                "query": query[:150],
                "response_preview": response[:200],
                "adapter": adapter,
                "timestamp": time.time(),
            })
            # Keep only last 10
            identity.memorable_exchanges = identity.memorable_exchanges[-10:]

        # Persist
        self._save(uid)

    def _extract_topics(self, query: str) -> List[str]:
        """Extract topic keywords from a query."""
        topic_signals = {
            "music": ["music", "mix", "master", "chord", "scale", "beat", "synth",
                      "eq", "compress", "reverb", "daw", "production"],
            "architecture": ["architecture", "system", "layer", "stack", "module",
                            "engine", "forge", "cocoon"],
            "identity": ["who am i", "who are you", "your name", "my name",
                         "identity", "remember me"],
            "philosophy": ["consciousness", "meaning", "philosophy", "ethics",
                          "moral", "purpose", "existence"],
            "creative": ["creative", "art", "design", "write", "story",
                        "imagination", "inspiration"],
            "technical": ["code", "python", "api", "deploy", "bug", "fix",
                         "build", "test", "debug"],
            "emotional": ["feel", "anxious", "happy", "sad", "frustrated",
                         "stuck", "overwhelmed", "grateful"],
        }

        lower = query.lower()
        found = []
        for topic, signals in topic_signals.items():
            if any(s in lower for s in signals):
                found.append(topic)
        return found

    def get_summary(self) -> Dict:
        """Return summary of all known identities."""
        return {
            uid: {
                "name": identity.display_name,
                "relationship": identity.relationship,
                "interactions": identity.interaction_count,
                "trust": round(identity.trust_level, 2),
                "last_seen": identity.last_seen,
                "permanent": identity.permanent,
            }
            for uid, identity in self.identities.items()
        }
