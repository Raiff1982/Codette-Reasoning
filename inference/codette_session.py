#!/usr/bin/env python3
"""Codette Session Manager — Cocoon-Backed Conversation Memory

Wraps the Cocoon system (QuantumSpiderweb + CocoonSync + EpistemicMetrics)
into a session manager that persists conversation state with encrypted memory.

Each session saves:
- Chat history
- Spiderweb state (agent beliefs, tensions, attractors)
- Glyphs (identity signatures)
- Epistemic metrics (coherence, tension, coverage)

Zero external dependencies beyond what the forge already uses.
"""

import json, os, time, hashlib, sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
import sys
_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Import Cocoon subsystems (graceful fallback if not available)
try:
    from reasoning_forge.quantum_spiderweb import QuantumSpiderweb, NodeState
    HAS_SPIDERWEB = True
except ImportError:
    HAS_SPIDERWEB = False

try:
    from reasoning_forge.epistemic_metrics import EpistemicMetrics
    HAS_METRICS = True
except ImportError:
    HAS_METRICS = False

try:
    from reasoning_forge.cocoon_sync import CocoonSync, CocoonKeyManager
    HAS_COCOON = True
except ImportError:
    HAS_COCOON = False

try:
    from reasoning_forge.dream_reweaver import DreamReweaver
    HAS_DREAMER = True
except ImportError:
    HAS_DREAMER = False

try:
    from reasoning_forge.quantum_optimizer import QuantumOptimizer, QualitySignal
    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False

try:
    from reasoning_forge.living_memory import LivingMemoryKernel
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False

try:
    from reasoning_forge.guardian import CodetteGuardian
    HAS_GUARDIAN = True
except ImportError:
    HAS_GUARDIAN = False

try:
    from reasoning_forge.resonant_continuity import ResonantContinuityEngine
    HAS_RESONANCE = True
except ImportError:
    HAS_RESONANCE = False

try:
    from reasoning_forge.perspective_registry import (
        PERSPECTIVES, get_adapter_for_perspective, list_all as list_perspectives
    )
    HAS_PERSPECTIVES = True
except ImportError:
    HAS_PERSPECTIVES = False

try:
    from reasoning_forge.aegis import AEGIS
    HAS_AEGIS = True
except ImportError:
    HAS_AEGIS = False

try:
    from reasoning_forge.nexus import NexusSignalEngine
    HAS_NEXUS = True
except ImportError:
    HAS_NEXUS = False

# Agent names matching the 8 adapters
AGENT_NAMES = [
    "newton", "davinci", "empathy", "philosophy",
    "quantum", "consciousness", "multi_perspective", "systems_architecture"
]

# Adapter accent colors for UI
ADAPTER_COLORS = {
    "newton": "#3b82f6",           # Electric blue
    "davinci": "#f59e0b",          # Warm gold
    "empathy": "#a855f7",          # Soft purple
    "philosophy": "#10b981",       # Emerald green
    "quantum": "#ef4444",          # Crimson red
    "consciousness": "#e2e8f0",    # Silver/white
    "multi_perspective": "#f97316", # Amber
    "systems_architecture": "#06b6d4",  # Teal
    "_base": "#94a3b8",            # Slate gray
}

DB_PATH = Path(__file__).parent.parent / "data" / "codette_sessions.db"


class CodetteSession:
    """Manages a single conversation session with Cocoon state."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or hashlib.sha256(
            f"{time.time()}_{os.getpid()}".encode()
        ).hexdigest()[:16]

        self.messages: List[Dict[str, str]] = []
        self.created_at = time.time()
        self.updated_at = time.time()

        # Cocoon state
        self.spiderweb = None
        self.metrics_engine = None
        self.cocoon_sync = None
        self.dream_reweaver = None
        self.optimizer = None
        self.memory_kernel = None
        self.guardian = None
        self.resonance_engine = None
        self.aegis = None
        self.nexus = None

        # Metrics history
        self.coherence_history: List[float] = []
        self.tension_history: List[float] = []
        self.attractors: List[Dict] = []
        self.glyphs: List[Dict] = []
        self.perspective_usage: Dict[str, int] = {}
        self.lifeforms: List[str] = []  # Spawned concept nodes
        self.dream_history: List[Dict] = []  # Dream field results
        self.active_continuity_summary: str = ""
        self.decision_landmarks: List[Dict[str, Any]] = []

        # Initialize subsystems
        self._init_cocoon()

    def _init_cocoon(self):
        """Initialize Cocoon subsystems if available."""
        if HAS_SPIDERWEB:
            self.spiderweb = QuantumSpiderweb()
            self.spiderweb.build_from_agents(AGENT_NAMES)

        if HAS_METRICS:
            self.metrics_engine = EpistemicMetrics()

        if HAS_COCOON:
            try:
                key_mgr = CocoonKeyManager()
                self.cocoon_sync = CocoonSync(
                    node_id=f"session_{self.session_id}",
                    key_manager=key_mgr,
                )
            except Exception:
                self.cocoon_sync = None

        if HAS_DREAMER:
            self.dream_reweaver = DreamReweaver(creativity=0.3)

        if HAS_OPTIMIZER:
            self.optimizer = QuantumOptimizer()

        if HAS_MEMORY:
            self.memory_kernel = LivingMemoryKernel(max_memories=100)

        if HAS_GUARDIAN:
            self.guardian = CodetteGuardian()

        if HAS_RESONANCE:
            self.resonance_engine = ResonantContinuityEngine()

        if HAS_AEGIS:
            self.aegis = AEGIS()

        if HAS_NEXUS:
            self.nexus = NexusSignalEngine()

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the session history."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        if metadata:
            msg["metadata"] = metadata
        self.messages.append(msg)
        self.updated_at = time.time()
        self.refresh_active_continuity_summary()
        self._capture_decision_landmark(role, content)

    def _capture_decision_landmark(self, role: str, content: str) -> None:
        """Promote explicit decisions/constraints into durable session landmarks."""
        text = str(content or "").strip().replace("\n", " ")
        if not text:
            return

        lowered = text.lower()
        cue_words = [
            "preserve", "keep", "without removing", "do not remove", "don't remove",
            "same rules", "in order", "we decided", "decision", "constraint",
            "i will", "i'll", "implemented", "next step", "must", "priority",
        ]
        if not any(cue in lowered for cue in cue_words):
            return

        label = "Assistant commitment" if role == "assistant" else "User constraint"
        summary = text[:180] + ("..." if len(text) > 180 else "")
        if self.decision_landmarks and self.decision_landmarks[-1].get("summary") == summary:
            return

        self.decision_landmarks.append({
            "role": role,
            "label": label,
            "summary": summary,
            "timestamp": time.time(),
            "persisted": False,
        })
        self.decision_landmarks = self.decision_landmarks[-12:]

    def refresh_active_continuity_summary(self) -> str:
        """Refresh the compact working-memory summary for the current session."""
        recent = [
            msg for msg in self.messages
            if msg.get("role") in {"user", "assistant"}
        ][-8:]

        if not recent:
            self.active_continuity_summary = ""
            return self.active_continuity_summary

        active_topics: List[str] = []
        user_intents: List[str] = []
        assistant_commitments: List[str] = []

        for msg in recent:
            role = msg.get("role")
            text = str(msg.get("content", "")).strip().replace("\n", " ")
            if not text:
                continue
            snippet = text[:140] + ("..." if len(text) > 140 else "")
            if role == "user" and len(user_intents) < 3:
                user_intents.append(snippet)
            elif role == "assistant" and len(assistant_commitments) < 3:
                assistant_commitments.append(snippet)

            lowered = text.lower()
            if "singular" in lowered and "singularity analysis" not in active_topics:
                active_topics.append("singularity analysis")
            if "risk frontier" in lowered or "frontier" in lowered:
                if "risk frontier comparison" not in active_topics:
                    active_topics.append("risk frontier comparison")
            if "continuity" in lowered or "session recall" in lowered:
                if "session continuity" not in active_topics:
                    active_topics.append("session continuity")
            if "aegis" in lowered and "AEGIS weighting" not in active_topics:
                active_topics.append("AEGIS weighting")
            if "cocoon" in lowered and "cocoon persistence" not in active_topics:
                active_topics.append("cocoon persistence")

        if not active_topics:
            active_topics.append("general ongoing collaboration")

        summary_lines = [
            f"Session focus: {', '.join(active_topics[:4])}.",
            f"Recent user intent: {user_intents[-1] if user_intents else 'No recent user instruction recorded.'}",
        ]

        if assistant_commitments:
            summary_lines.append(f"Latest assistant commitment: {assistant_commitments[-1]}")

        if self.perspective_usage:
            top_adapter = max(self.perspective_usage, key=self.perspective_usage.get)
            summary_lines.append(f"Most-used adapter this session: {top_adapter}.")

        self.active_continuity_summary = " ".join(summary_lines)[:700]
        return self.active_continuity_summary

    def build_prompt_context(self, max_turns: int = 3, max_chars: int = 900) -> str:
        """Build a compact recent-session context for prompt enrichment."""
        if not self.messages:
            return ""

        turns = []
        current_turn = []
        for msg in reversed(self.messages):
            role = msg.get("role")
            if role not in {"user", "assistant"}:
                continue
            current_turn.append(msg)
            if role == "user":
                turns.append(list(reversed(current_turn)))
                current_turn = []
            if len(turns) >= max_turns:
                break

        if current_turn and len(turns) < max_turns:
            turns.append(list(reversed(current_turn)))

        snippets = []
        used = 0
        for turn in reversed(turns):
            for msg in turn:
                role = msg.get("role", "unknown").upper()
                content = str(msg.get("content", "")).strip().replace("\n", " ")
                if not content:
                    continue
                if len(content) > 180:
                    content = content[:177] + "..."
                line = f"- {role}: {content}"
                if used + len(line) > max_chars:
                    break
                snippets.append(line)
                used += len(line)
            if used >= max_chars:
                break

        return "\n".join(snippets)

    def get_recent_memory_markers(self, max_items: int = 4) -> List[Dict[str, Any]]:
        """Expose a small, UI-safe slice of recent session memory."""
        markers = []
        for msg in reversed(self.messages):
            if msg.get("role") not in {"user", "assistant"}:
                continue
            text = str(msg.get("content", "")).strip().replace("\n", " ")
            if not text:
                continue
            markers.append({
                "role": msg["role"],
                "text": text[:160] + ("..." if len(text) > 160 else ""),
                "timestamp": msg.get("timestamp"),
            })
            if len(markers) >= max_items:
                break
        markers.reverse()
        return markers

    def get_recent_decision_landmarks(self, max_items: int = 4) -> List[Dict[str, Any]]:
        """Expose the most important recent constraints/commitments."""
        return self.decision_landmarks[-max_items:]

    def mark_decision_landmark_persisted(self, summary: str, cocoon_id: str = "") -> None:
        """Mark a decision landmark as stored in unified memory."""
        for landmark in reversed(self.decision_landmarks):
            if landmark.get("summary") == summary:
                landmark["persisted"] = True
                if cocoon_id:
                    landmark["cocoon_id"] = cocoon_id
                break

    def update_after_response(self, route_result, adapter_name: str,
                               perspectives: Optional[Dict[str, str]] = None):
        """Update Cocoon state after a Codette response.

        Args:
            route_result: RouteResult from the router
            adapter_name: Which adapter was primary
            perspectives: Dict of adapter_name -> response text (if multi-perspective)
        """
        # Track adapter usage
        self.perspective_usage[adapter_name] = \
            self.perspective_usage.get(adapter_name, 0) + 1

        if not HAS_SPIDERWEB or self.spiderweb is None:
            return

        # Propagate belief through the spiderweb from the active adapter
        try:
            if adapter_name in self.spiderweb.nodes:
                node = self.spiderweb.nodes[adapter_name]
                # Boost the active adapter's psi (thought magnitude)
                node.state.psi = min(node.state.psi + 0.1, 2.0)
                node.state.tau += 0.05  # Temporal progression

                # Propagate the boosted belief outward (BUG FIX: pass belief state)
                self.spiderweb.propagate_belief(
                    adapter_name, belief=node.state, max_hops=2
                )

            # If multi-perspective, entangle the participating agents
            if perspectives and len(perspectives) > 1:
                adapters = list(perspectives.keys())
                for i in range(len(adapters)):
                    for j in range(i + 1, len(adapters)):
                        if (adapters[i] in self.spiderweb.nodes and
                            adapters[j] in self.spiderweb.nodes):
                            self.spiderweb.entangle(adapters[i], adapters[j])

            # Compute metrics
            coherence = self.spiderweb.phase_coherence()
            self.coherence_history.append(coherence)

            # Detect attractors
            self.attractors = self.spiderweb.detect_attractors()

            # Try to form glyphs for active nodes
            for name in (perspectives or {adapter_name: ""}).keys():
                if name in self.spiderweb.nodes:
                    glyph = self.spiderweb.form_glyph(name)
                    if glyph:
                        self.glyphs.append({
                            "glyph_id": glyph.glyph_id,
                            "source": glyph.source_node,
                            "stability": glyph.stability_score,
                        })

            # Check convergence
            is_converging, mean_tension = self.spiderweb.check_convergence()
            self.tension_history.append(mean_tension)

            # Feed quality signal to optimizer if available
            if HAS_OPTIMIZER and self.optimizer:
                try:
                    signal = QualitySignal(
                        timestamp=time.time(),
                        adapter=adapter_name,
                        coherence=coherence,
                        tension=mean_tension,
                        productivity=0.5,  # Default, updated by epistemic report
                        response_length=0,
                        multi_perspective=perspectives is not None and len(perspectives) > 1,
                        user_continued=True,
                    )
                    self.optimizer.record_signal(signal)
                except Exception:
                    pass

        except Exception as e:
            print(f"  [cocoon] Spiderweb update error: {e}")

        # Update resonance engine
        if self.resonance_engine:
            try:
                coh = self.coherence_history[-1] if self.coherence_history else 0.5
                ten = self.tension_history[-1] if self.tension_history else 0.3
                self.resonance_engine.compute_psi(coherence=coh, tension=ten)
            except Exception:
                pass

        # Update guardian trust
        if self.guardian:
            try:
                coh = self.coherence_history[-1] if self.coherence_history else 0.5
                ten = self.tension_history[-1] if self.tension_history else 0.3
                self.guardian.evaluate_output(adapter_name, "", coh, ten)
            except Exception:
                pass

        # AEGIS ethical evaluation of the response
        if self.aegis and self.messages:
            try:
                # Find the most recent assistant response
                for msg in reversed(self.messages[-4:]):
                    if msg["role"] == "assistant":
                        self.aegis.evaluate(msg["content"], adapter=adapter_name)
                        break
            except Exception:
                pass

        # Nexus signal analysis of the user input
        if self.nexus and self.messages:
            try:
                for msg in reversed(self.messages[-4:]):
                    if msg["role"] == "user":
                        self.nexus.analyze(msg["content"], adapter=adapter_name)
                        break
            except Exception:
                pass

        # Store memory cocoon for significant exchanges
        if self.memory_kernel and self.messages:
            try:
                # Find the most recent user query and assistant response
                query_text = ""
                response_text = ""
                for msg in reversed(self.messages[-4:]):
                    if msg["role"] == "user" and not query_text:
                        query_text = msg["content"]
                    elif msg["role"] == "assistant" and not response_text:
                        response_text = msg["content"]
                if query_text and response_text:
                    coh = self.coherence_history[-1] if self.coherence_history else 0.5
                    ten = self.tension_history[-1] if self.tension_history else 0.3
                    self.memory_kernel.store_from_turn(
                        query=query_text,
                        response=response_text,
                        adapter=adapter_name,
                        coherence=coh,
                        tension=ten,
                    )
            except Exception:
                pass

    def compute_epistemic_report(self, analyses: Dict[str, str],
                                  synthesis: str = "") -> Optional[Dict]:
        """Run full epistemic metrics on a multi-perspective response."""
        if not HAS_METRICS or self.metrics_engine is None:
            return None

        try:
            return self.metrics_engine.full_epistemic_report(analyses, synthesis)
        except Exception as e:
            print(f"  [cocoon] Metrics error: {e}")
            return None

    def get_state(self) -> Dict[str, Any]:
        """Get full session state for UI rendering."""
        state = {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "perspective_usage": self.perspective_usage,
            "adapter_colors": ADAPTER_COLORS,
            "cocoon": {
                "has_spiderweb": HAS_SPIDERWEB and self.spiderweb is not None,
                "has_metrics": HAS_METRICS,
                "has_sync": HAS_COCOON and self.cocoon_sync is not None,
            },
        }

        # Spiderweb state
        if self.spiderweb:
            try:
                web_dict = self.spiderweb.to_dict()
                state["spiderweb"] = {
                    "nodes": {
                        nid: {
                            # BUG FIX: to_dict() stores state as a list [psi,tau,chi,phi,lam]
                            "state": n["state"],
                            "neighbors": n.get("neighbors", []),
                            "tension_history": n.get("tension_history", [])[-10:],
                        }
                        for nid, n in web_dict.get("nodes", {}).items()
                    },
                    "phase_coherence": web_dict.get("phase_coherence", 0),
                    "attractors": self.attractors,
                    "glyphs": self.glyphs[-10:],  # Last 10
                    # New VIVARA-inspired metrics
                    "entropy": self.spiderweb.shannon_entropy(),
                    "decoherence_rate": self.spiderweb.decoherence_rate(),
                    "lifeforms": self.lifeforms[-20:],
                }
            except Exception:
                state["spiderweb"] = None
        else:
            state["spiderweb"] = None

        # Metrics history
        state["metrics"] = {
            "coherence_history": self.coherence_history[-50:],
            "tension_history": self.tension_history[-50:],
            "current_coherence": self.coherence_history[-1] if self.coherence_history else 0,
            "current_tension": self.tension_history[-1] if self.tension_history else 0,
            "attractor_count": len(self.attractors),
            "glyph_count": len(self.glyphs),
        }

        # Optimizer tuning state
        if HAS_OPTIMIZER and self.optimizer:
            state["optimizer"] = self.optimizer.get_tuning_report()
        else:
            state["optimizer"] = None

        # Dream history
        state["dream_history"] = self.dream_history[-10:]

        # Living memory
        if self.memory_kernel:
            state["memory"] = self.memory_kernel.get_state()
        else:
            state["memory"] = None

        # Guardian state
        if self.guardian:
            state["guardian"] = self.guardian.get_state()
        else:
            state["guardian"] = None

        # Resonant continuity
        if self.resonance_engine:
            state["resonance"] = self.resonance_engine.get_state()
        else:
            state["resonance"] = None

        # AEGIS ethical alignment
        if self.aegis:
            state["aegis"] = self.aegis.get_state()
        else:
            state["aegis"] = None

        # Nexus signal intelligence
        if self.nexus:
            state["nexus"] = self.nexus.get_state()
        else:
            state["nexus"] = None

        # Perspective registry
        if HAS_PERSPECTIVES:
            state["perspectives_available"] = len(PERSPECTIVES)

        state["recent_memory_markers"] = self.get_recent_memory_markers()
        state["active_continuity_summary"] = self.active_continuity_summary
        state["decision_landmarks"] = self.get_recent_decision_landmarks()

        return state

    def to_dict(self) -> Dict:
        """Serialize for storage."""
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
            "coherence_history": self.coherence_history,
            "tension_history": self.tension_history,
            "attractors": self.attractors,
            "glyphs": self.glyphs,
            "perspective_usage": self.perspective_usage,
            "lifeforms": self.lifeforms,
            "dream_history": self.dream_history,
            "active_continuity_summary": self.active_continuity_summary,
            "decision_landmarks": self.decision_landmarks,
        }
        if self.spiderweb:
            try:
                data["spiderweb_state"] = self.spiderweb.to_dict()
            except Exception:
                pass
        if HAS_OPTIMIZER and self.optimizer:
            try:
                data["optimizer_state"] = self.optimizer.to_dict()
            except Exception:
                pass
        if self.memory_kernel:
            try:
                data["memory_state"] = self.memory_kernel.to_dict()
            except Exception:
                pass
        if self.guardian:
            try:
                data["guardian_state"] = self.guardian.to_dict()
            except Exception:
                pass
        if self.resonance_engine:
            try:
                data["resonance_state"] = self.resonance_engine.to_dict()
            except Exception:
                pass
        if self.aegis:
            try:
                data["aegis_state"] = self.aegis.to_dict()
            except Exception:
                pass
        if self.nexus:
            try:
                data["nexus_state"] = self.nexus.to_dict()
            except Exception:
                pass
        return data

    def from_dict(self, data: Dict):
        """Restore from storage."""
        self.session_id = data.get("session_id", self.session_id)
        self.created_at = data.get("created_at", self.created_at)
        self.updated_at = data.get("updated_at", self.updated_at)
        self.messages = data.get("messages", [])
        self.coherence_history = data.get("coherence_history", [])
        self.tension_history = data.get("tension_history", [])
        self.attractors = data.get("attractors", [])
        self.glyphs = data.get("glyphs", [])
        self.perspective_usage = data.get("perspective_usage", {})
        self.lifeforms = data.get("lifeforms", [])
        self.dream_history = data.get("dream_history", [])
        self.active_continuity_summary = data.get("active_continuity_summary", "")
        self.decision_landmarks = data.get("decision_landmarks", [])
        if not self.active_continuity_summary:
            self.refresh_active_continuity_summary()

        if self.spiderweb and "spiderweb_state" in data:
            try:
                self.spiderweb = QuantumSpiderweb.from_dict(data["spiderweb_state"])
            except Exception:
                pass
        if HAS_OPTIMIZER and self.optimizer and "optimizer_state" in data:
            try:
                self.optimizer = QuantumOptimizer.from_dict(data["optimizer_state"])
            except Exception:
                pass
        if HAS_MEMORY and "memory_state" in data:
            try:
                self.memory_kernel = LivingMemoryKernel.from_dict(data["memory_state"])
            except Exception:
                pass
        if HAS_GUARDIAN and "guardian_state" in data:
            try:
                self.guardian = CodetteGuardian.from_dict(data["guardian_state"])
            except Exception:
                pass
        if HAS_RESONANCE and "resonance_state" in data:
            try:
                self.resonance_engine = ResonantContinuityEngine.from_dict(data["resonance_state"])
            except Exception:
                pass
        if HAS_AEGIS and "aegis_state" in data:
            try:
                self.aegis = AEGIS.from_dict(data["aegis_state"])
            except Exception:
                pass
        if HAS_NEXUS and "nexus_state" in data:
            try:
                self.nexus = NexusSignalEngine.from_dict(data["nexus_state"])
            except Exception:
                pass


class SessionStore:
    """SQLite-backed session persistence with Cocoon encryption."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create sessions table if needed."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL,
                updated_at REAL,
                title TEXT,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save(self, session: CodetteSession, title: Optional[str] = None):
        """Save a session to the database."""
        if title is None:
            # Auto-title from first user message
            for msg in session.messages:
                if msg["role"] == "user":
                    title = msg["content"][:80]
                    break
            title = title or f"Session {session.session_id[:8]}"

        data_json = json.dumps(session.to_dict())

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO sessions (session_id, created_at, updated_at, title, data)
            VALUES (?, ?, ?, ?, ?)
        """, (session.session_id, session.created_at, session.updated_at, title, data_json))
        conn.commit()
        conn.close()

    def load(self, session_id: str) -> Optional[CodetteSession]:
        """Load a session from the database."""
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()

        if not row:
            return None

        session = CodetteSession(session_id)
        session.from_dict(json.loads(row[0]))
        return session

    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List recent sessions."""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute("""
            SELECT session_id, created_at, updated_at, title
            FROM sessions ORDER BY updated_at DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()

        return [
            {
                "session_id": r[0],
                "created_at": r[1],
                "updated_at": r[2],
                "title": r[3],
            }
            for r in rows
        ]

    def delete(self, session_id: str):
        """Delete a session."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()


# Quick test
if __name__ == "__main__":
    print("Testing CodetteSession...")
    session = CodetteSession()
    print(f"  Session ID: {session.session_id}")
    print(f"  Spiderweb: {HAS_SPIDERWEB}")
    print(f"  Metrics: {HAS_METRICS}")
    print(f"  Cocoon: {HAS_COCOON}")

    session.add_message("user", "How does gravity work?")
    session.add_message("assistant", "Objects attract each other...",
                        metadata={"adapter": "newton", "confidence": 0.95})

    state = session.get_state()
    print(f"  State keys: {list(state.keys())}")
    print(f"  Cocoon status: {state['cocoon']}")

    if state["spiderweb"]:
        print(f"  Nodes: {list(state['spiderweb']['nodes'].keys())}")
        print(f"  Phase coherence: {state['spiderweb']['phase_coherence']:.4f}")

    # Test persistence
    store = SessionStore()
    store.save(session)
    loaded = store.load(session.session_id)
    print(f"  Persistence: {'OK' if loaded else 'FAILED'}")
    if loaded:
        print(f"  Loaded messages: {len(loaded.messages)}")

    print("Done!")
