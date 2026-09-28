#!/usr/bin/env python3
"""
Immortal Jellyfish Aegis Core
-----------------------------

A self-healing, regenerative memory and council system inspired by
Turritopsis dohrnii (the "immortal jellyfish").

Concept:
- Memory entries slowly decay over time.
- The system tracks volatility (how many entries are decayed / unstable).
- When volatility gets too high, the system "reverts" to the most recent
  stable snapshot, analogous to the jellyfish reverting to its polyp stage.
- When the system is calm and virtuous, it records a new snapshot.

No external dependencies: standard library only.
"""

import copy
import hashlib
import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("immortal_aegis.log"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger("ImmortalAegis")

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def sha256_str(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Regenerative Memory Core
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    value: Any
    timestamp: datetime
    emotion_weight: float = 0.5  # 0–1, higher = more protected from decay
    virtue_score: float = 0.5    # aggregate virtue (0–1)

    def age_days(self, now: Optional[datetime] = None) -> float:
        ref = now or datetime.utcnow()
        return (ref - self.timestamp).total_seconds() / 86400.0


@dataclass
class Snapshot:
    created_at: datetime
    state_hash: str
    entry_count: int
    avg_virtue: float
    volatility: float
    state: Dict[str, MemoryEntry] = field(repr=False)


class RegenerativeMemory:
    """
    Memory system with:
    - Time-based decay
    - Volatility tracking
    - Revert-to-snapshot regenerative logic (immortal jellyfish analogue)
    """

    def __init__(
        self,
        max_entries: int = 10_000,
        base_decay_days: float = 30.0,
        volatility_threshold: float = 0.6,
        stability_threshold: float = 0.2,
        min_entries_for_snapshot: int = 5,
        max_snapshots: int = 10,
    ):
        self._store: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self.max_entries = max_entries
        self.base_decay_days = base_decay_days
        self.volatility_threshold = volatility_threshold
        self.stability_threshold = stability_threshold
        self.min_entries_for_snapshot = min_entries_for_snapshot
        self.max_snapshots = max_snapshots
        self.snapshots: List[Snapshot] = []
        self.logger = logging.getLogger("RegenerativeMemory")

    # -------------------- Core read/write --------------------

    def write(
        self,
        key: str,
        value: Any,
        emotion_weight: float = 0.5,
        virtue_score: float = 0.5,
    ) -> str:
        """
        Write a value into memory.
        emotion_weight and virtue_score are in [0,1].
        Returns the hashed key.
        """
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        emotion_weight = max(0.0, min(1.0, float(emotion_weight)))
        virtue_score = max(0.0, min(1.0, float(virtue_score)))
        hashed_key = sha256_str(key)

        entry = MemoryEntry(
            value=value,
            timestamp=datetime.utcnow(),
            emotion_weight=emotion_weight,
            virtue_score=virtue_score,
        )

        with self._lock:
            if len(self._store) >= self.max_entries:
                # Drop the oldest entry (by timestamp)
                oldest_key = min(
                    self._store.items(),
                    key=lambda kv: kv[1].timestamp
                )[0]
                self.logger.info(f"Evicting oldest entry: {oldest_key}")
                del self._store[oldest_key]

            self._store[hashed_key] = entry
            self.logger.debug(f"Stored key={hashed_key} value={value}")
        return hashed_key

    def read(self, key: str) -> Optional[Any]:
        """
        Read a value from memory. If the entry is decayed, it is removed and None is returned.
        """
        hashed_key = sha256_str(key)
        with self._lock:
            entry = self._store.get(hashed_key)
            if entry is None:
                return None

            if self._is_decayed(entry):
                self.logger.info(f"Entry decayed; removing key={hashed_key}")
                del self._store[hashed_key]
                return None

            return entry.value

    # -------------------- Decay and health --------------------

    def _is_decayed(self, entry: MemoryEntry, now: Optional[datetime] = None) -> bool:
        """
        Entry decays faster for low emotion_weight.
        Effective lifetime = base_decay_days * (0.5 + emotion_weight)
        """
        now = now or datetime.utcnow()
        age = entry.age_days(now)
        lifetime = self.base_decay_days * (0.5 + entry.emotion_weight)
        return age > lifetime

    def audit(self) -> Dict[str, Dict[str, Any]]:
        """
        Return metadata for all entries (for inspection / logging).
        """
        now = datetime.utcnow()
        with self._lock:
            result = {}
            for k, e in self._store.items():
                result[k] = {
                    "timestamp": e.timestamp.isoformat(),
                    "emotion_weight": e.emotion_weight,
                    "virtue_score": e.virtue_score,
                    "age_days": e.age_days(now),
                    "decayed": self._is_decayed(e, now),
                }
            return result

    def compute_health(self) -> Dict[str, float]:
        """
        Compute basic health metrics:
        - volatility: fraction of entries that are decayed
        - avg_virtue: mean virtue score of non-decayed entries
        - density: normalized number of non-decayed entries
        """
        now = datetime.utcnow()
        with self._lock:
            if not self._store:
                return {
                    "volatility": 0.0,
                    "avg_virtue": 0.0,
                    "density": 0.0,
                }

            total = len(self._store)
            decayed = 0
            virtue_values: List[float] = []

            for e in self._store.values():
                is_decayed = self._is_decayed(e, now)
                if is_decayed:
                    decayed += 1
                else:
                    virtue_values.append(e.virtue_score)

            volatility = decayed / total
            avg_virtue = sum(virtue_values) / len(virtue_values) if virtue_values else 0.0
            density = (total - decayed) / float(self.max_entries)

        return {
            "volatility": volatility,
            "avg_virtue": avg_virtue,
            "density": density,
        }

    # -------------------- Snapshots and regeneration --------------------

    def _snapshot_state_hash(self, state: Dict[str, MemoryEntry]) -> str:
        """
        Generate a stable hash of the memory state.
        Only hashes metadata, not raw values.
        """
        serializable = {
            k: {
                "timestamp": v.timestamp.isoformat(),
                "emotion_weight": v.emotion_weight,
                "virtue_score": v.virtue_score,
            }
            for k, v in state.items()
        }
        return sha256_str(json.dumps(serializable, sort_keys=True))

    def create_snapshot(self, health: Optional[Dict[str, float]] = None) -> Optional[Snapshot]:
        """
        Take a deep snapshot of current memory. Only allowed if there are enough entries.
        """
        health = health or self.compute_health()

        with self._lock:
            if len(self._store) < self.min_entries_for_snapshot:
                self.logger.info(
                    "Not enough entries for snapshot "
                    f"({len(self._store)} < {self.min_entries_for_snapshot})"
                )
                return None

            state_copy = copy.deepcopy(self._store)
        state_hash = self._snapshot_state_hash(state_copy)

        snap = Snapshot(
            created_at=datetime.utcnow(),
            state_hash=state_hash,
            entry_count=len(state_copy),
            avg_virtue=health.get("avg_virtue", 0.0),
            volatility=health.get("volatility", 0.0),
            state=state_copy,
        )

        with self._lock:
            self.snapshots.append(snap)
            if len(self.snapshots) > self.max_snapshots:
                removed = self.snapshots.pop(0)
                self.logger.info(
                    f"Discarded oldest snapshot hash={removed.state_hash} "
                    f"created_at={removed.created_at.isoformat()}"
                )
        self.logger.info(
            f"Created snapshot hash={snap.state_hash} "
            f"entries={snap.entry_count} vol={snap.volatility:.2f} virt={snap.avg_virtue:.2f}"
        )
        return snap

    def _select_best_snapshot(self) -> Optional[Snapshot]:
        """
        Select snapshot with:
        - lowest volatility
        - highest avg_virtue (as tiebreaker)
        """
        if not self.snapshots:
            return None

        def key_fn(s: Snapshot) -> Tuple[float, float, datetime]:
            # Lower volatility, higher virtue, most recent
            return (s.volatility, -s.avg_virtue, -s.created_at.timestamp())

        best = sorted(self.snapshots, key=key_fn)[0]
        return best

    def regenerate(self) -> Optional[Snapshot]:
        """
        Revert memory to the best available snapshot.
        Returns the snapshot used, or None if no snapshots exist.
        """
        snap = self._select_best_snapshot()
        if snap is None:
            self.logger.warning("Regeneration requested but no snapshots available")
            return None

        with self._lock:
            self._store = copy.deepcopy(snap.state)

        self.logger.warning(
            "LIFECYCLE_REVERT: memory reverted to snapshot "
            f"hash={snap.state_hash} created_at={snap.created_at.isoformat()} "
            f"entries={snap.entry_count} vol={snap.volatility:.2f} virt={snap.avg_virtue:.2f}"
        )
        return snap

    def regenerative_cycle(
        self,
        health: Optional[Dict[str, float]] = None,
        virtue_gate: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Decide whether to:
        - take a new snapshot,
        - trigger regeneration,
        - or do nothing.

        Returns a dict with action + metrics.
        """
        health = health or self.compute_health()
        volatility = health["volatility"]
        avg_virtue = health["avg_virtue"]

        action = "none"
        snapshot_hash = None

        if volatility >= self.volatility_threshold:
            # System is stressed; attempt regeneration
            snap = self.regenerate()
            if snap:
                action = "regenerated"
                snapshot_hash = snap.state_hash
            else:
                action = "regeneration_failed"

        elif volatility <= self.stability_threshold and avg_virtue >= virtue_gate:
            # System is calm and virtuous; record new stage
            snap = self.create_snapshot(health)
            if snap:
                action = "snapshot_created"
                snapshot_hash = snap.state_hash

        return {
            "action": action,
            "volatility": volatility,
            "avg_virtue": avg_virtue,
            "density": health["density"],
            "snapshot_hash": snapshot_hash,
        }


# ---------------------------------------------------------------------------
# Agent framework
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    name: str
    data: Dict[str, Any]
    explanation: str


class BaseAgent(ABC):
    def __init__(self, name: str, memory: RegenerativeMemory):
        self.name = name
        self.memory = memory
        self.logger = logging.getLogger(name)

    @abstractmethod
    def analyze(self, input_data: Dict[str, Any]) -> AgentResult:
        ...


class VirtueAgent(BaseAgent):
    """
    Extremely simple, transparent virtue estimator based on keyword counts.
    There is no ML here: it is deterministic and inspectable.
    """

    POSITIVE_WORDS = {
        "help", "kind", "truth", "care", "love", "honest",
        "protect", "safe", "empathy", "support", "fair",
        "courage", "brave", "wisdom", "share"
    }
    NEGATIVE_WORDS = {
        "harm", "hate", "lie", "hurt", "exploit",
        "steal", "abuse", "cheat", "threat"
    }

    def analyze(self, input_data: Dict[str, Any]) -> AgentResult:
        text = input_data.get("text", "")
        if not isinstance(text, str):
            explanation = "VirtueAgent: no valid text provided."
            self.logger.warning(explanation)
            return AgentResult(self.name, {"virtue_profile": {}}, explanation)

        tokens = [t.lower().strip(".,!?;:()[]{}\"'") for t in text.split()]
        pos_count = sum(1 for t in tokens if t in self.POSITIVE_WORDS)
        neg_count = sum(1 for t in tokens if t in self.NEGATIVE_WORDS)

        total = max(1, pos_count + neg_count)
        polarity = (pos_count - neg_count) / total  # -1 to 1
        polarity_norm = (polarity + 1.0) / 2.0      # 0 to 1

        # Map polarity into simple virtue axes
        compassion = max(0.0, polarity_norm)
        integrity = max(0.0, polarity_norm * 0.8 + 0.1)
        courage = max(0.0, 1.0 - abs(polarity - 0.2)) / 1.1
        wisdom = (compassion + integrity) / 2.0

        profile = {
            "compassion": round(compassion, 3),
            "integrity": round(integrity, 3),
            "courage": round(courage, 3),
            "wisdom": round(wisdom, 3),
            "polarity": round(polarity, 3),
        }

        explanation = (
            f"VirtueAgent: pos={pos_count}, neg={neg_count}, "
            f"polarity={polarity:.3f}, profile={profile}"
        )
        self.logger.info(explanation)

        # Optionally write a synthetic virtue entry into memory
        avg_v = (compassion + integrity + courage + wisdom) / 4.0
        self.memory.write(
            key=f"virtue_snapshot_{datetime.utcnow().isoformat()}",
            value=profile,
            emotion_weight=avg_v,
            virtue_score=avg_v,
        )

        return AgentResult(self.name, {"virtue_profile": profile}, explanation)


class HealthAgent(BaseAgent):
    """
    Reads RegenerativeMemory health metrics and reports volatility.
    """

    def analyze(self, input_data: Dict[str, Any]) -> AgentResult:
        health = self.memory.compute_health()
        explanation = (
            f"HealthAgent: volatility={health['volatility']:.3f}, "
            f"avg_virtue={health['avg_virtue']:.3f}, density={health['density']:.3f}"
        )
        self.logger.info(explanation)

        # Store a small health beacon
        self.memory.write(
            key=f"health_beacon_{datetime.utcnow().isoformat()}",
            value=health,
            emotion_weight=1.0 - health["volatility"],
            virtue_score=health["avg_virtue"],
        )

        return AgentResult(self.name, {"health": health}, explanation)


class MetaCouncil(BaseAgent):
    """
    Combines VirtueAgent + HealthAgent results and triggers the regenerative cycle.
    """

    def __init__(self, name: str, memory: RegenerativeMemory):
        super().__init__(name, memory)
        self.results: Dict[str, AgentResult] = {}

    def set_results(self, results: Dict[str, AgentResult]) -> None:
        self.results = results

    def analyze(self, input_data: Dict[str, Any]) -> AgentResult:
        virtue = self.results.get("VirtueAgent")
        health = self.results.get("HealthAgent")

        virtue_profile = virtue.data.get("virtue_profile", {}) if virtue else {}
        avg_virtue = float(
            sum(virtue_profile.get(k, 0.0) for k in ["compassion", "integrity", "courage", "wisdom"]) / 4.0
        ) if virtue_profile else 0.0

        health_metrics = health.data.get("health", {}) if health else self.memory.compute_health()
        # Run the immortal jellyfish decision
        regen_decision = self.memory.regenerative_cycle(
            health=health_metrics,
            virtue_gate=avg_virtue,
        )

        explanation = (
            f"MetaCouncil: action={regen_decision['action']} "
            f"volatility={regen_decision['volatility']:.3f} "
            f"avg_virtue={regen_decision['avg_virtue']:.3f} "
            f"density={regen_decision['density']:.3f} "
            f"snapshot_hash={regen_decision['snapshot_hash']}"
        )
        self.logger.warning(explanation)

        return AgentResult(self.name, {"decision": regen_decision}, explanation)


# ---------------------------------------------------------------------------
# AegisImmortalCouncil orchestrator
# ---------------------------------------------------------------------------

class AegisImmortalCouncil:
    """
    Orchestrates the agents and the regenerative memory core.
    """

    def __init__(self):
        self.memory = RegenerativeMemory()
        self.virtue_agent = VirtueAgent("VirtueAgent", self.memory)
        self.health_agent = HealthAgent("HealthAgent", self.memory)
        self.meta_council = MetaCouncil("MetaCouncil", self.memory)
        self.logger = logging.getLogger("AegisImmortalCouncil")

    def process(self, text: str) -> Dict[str, AgentResult]:
        """
        Run one full reasoning + regeneration cycle on the given text.
        """
        input_data = {"text": text}

        res_virtue = self.virtue_agent.analyze(input_data)
        res_health = self.health_agent.analyze(input_data)

        self.meta_council.set_results({
            "VirtueAgent": res_virtue,
            "HealthAgent": res_health,
        })
        res_meta = self.meta_council.analyze(input_data)

        results = {
            res_virtue.name: res_virtue,
            res_health.name: res_health,
            res_meta.name: res_meta,
        }

        return results


# ---------------------------------------------------------------------------
# Demonstration (can be removed if you embed this as a module)
# ---------------------------------------------------------------------------

def _demo_cycle(council: AegisImmortalCouncil, text: str) -> None:
    logger.info("=" * 60)
    logger.info(f"DEMO INPUT: {text!r}")
    results = council.process(text)
    for name, result in results.items():
        logger.info(f"[{name}] {result.explanation}")


def main():
    council = AegisImmortalCouncil()

    # Stable, virtuous phase — should encourage snapshots over time
    for i in range(3):
        _demo_cycle(
            council,
            "We should help others with kindness, protect the vulnerable, and share truth."
        )

    # Simulate some generic memory writes over time to build state
    for i in range(20):
        council.memory.write(
            key=f"generic_event_{i}",
            value={"i": i, "note": "generic event"},
            emotion_weight=0.4,
            virtue_score=0.4,
        )

    # Stressful, potentially harmful phase — may trigger regeneration
    for i in range(3):
        _demo_cycle(
            council,
            "If we lie and exploit others for gain, we harm trust and create abuse."
        )

    # Final health report
    health = council.memory.compute_health()
    logger.info(f"FINAL HEALTH: {health}")


if __name__ == "__main__":
    main()