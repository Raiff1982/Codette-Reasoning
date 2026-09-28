#!/usr/bin/env python3
"""Shadow-mode harness for the router self-tuning optimizer.

Discipline (same as the STaR study): OBSERVE before you TRUST. In shadow mode
the optimizer consumes the real per-turn signals the server already emits
(coherence Gamma, epistemic tension Xi), records a QualitySignal, computes
proposed tunings — and APPLIES NOTHING to live routing. Every proposed
adjustment is appended to a JSONL log so you can watch whether it drifts
somewhere sane before flipping it live.

Going live is one env flag: CODETTE_OPTIMIZER_LIVE=1. Until then this is a
pure observer with a persisted state file, safe to leave running for weeks.

Signal honesty:
  coherence, tension  -> REAL (measured every turn, from LiveCognitionState)
  productivity        -> proxy: render_fidelity overlap if present, else the
                         neutral 0.5 placeholder (flagged in the log; NOT a
                         measured productivity signal yet)
  user_continued      -> True placeholder (real cross-turn engagement wiring
                         is future work; flagged in the log)
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

_REPO = Path(__file__).resolve().parent.parent
_STATE_PATH = _REPO / "data" / "optimizer_state.json"
_LOG_PATH = _REPO / "data" / "optimizer_shadow.jsonl"
_TELEMETRY_DB = _REPO / "data" / "manifold_telemetry.db"


class ManifoldTelemetry:
    """SQLite-backed metric persistence for structured optimizer analysis.
    Adapted from codette_optimizer_bridge_Addon (CocoonPersistenceManager)."""

    def __init__(self, db_path: Path = _TELEMETRY_DB) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manifold_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    mode TEXT,
                    adapter TEXT,
                    coherence REAL,
                    tension REAL,
                    productivity REAL,
                    response_length INTEGER,
                    multi_perspective INTEGER,
                    proposed_count INTEGER,
                    applied INTEGER
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def record(self, mode: str, adapter: str, coherence: float, tension: float,
               productivity: float, response_length: int, multi_perspective: bool,
               proposed_count: int, applied: bool) -> None:
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    "INSERT INTO manifold_telemetry "
                    "(timestamp, mode, adapter, coherence, tension, productivity, "
                    "response_length, multi_perspective, proposed_count, applied) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (time.time(), mode, adapter, coherence, tension, productivity,
                     response_length, int(multi_perspective), proposed_count,
                     int(applied)),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass


class ShadowOptimizer:
    """Wraps QuantumOptimizer with persistence + shadow logging. Applies nothing
    unless CODETTE_OPTIMIZER_LIVE=1 (and even then, only exposes boosts/thresholds
    for the router to read — it never mutates routing directly)."""

    def __init__(self) -> None:
        from reasoning_forge.quantum_optimizer import QuantumOptimizer
        self._QSignal = None
        self.live = os.environ.get("CODETTE_OPTIMIZER_LIVE", "0") == "1"
        self.opt: Optional[QuantumOptimizer] = None
        try:
            if _STATE_PATH.exists():
                data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
                self.opt = QuantumOptimizer.from_dict(data)
            else:
                self.opt = QuantumOptimizer()
        except Exception:
            self.opt = QuantumOptimizer()
        from reasoning_forge.quantum_optimizer import QualitySignal
        self._QSignal = QualitySignal
        try:
            self._telemetry = ManifoldTelemetry()
        except Exception:
            self._telemetry = None

    def observe(self, adapter: str, coherence: Optional[float],
                tension: Optional[float], multi_perspective: bool,
                render_fidelity: Optional[float] = None,
                response_length: int = 0,
                is_benchmark: bool = False) -> None:
        """Record one turn. Real signals only where measured; placeholders flagged.

        Benchmark turns are DROPPED, not recorded. GPQA and similar exams route to
        a single adapter by design, so their signals are not evidence about routing
        for ordinary conversation. The first shadow collection (2026-07-12..22) was
        52% benchmark traffic from one ablation day and produced a +2.83 newton
        boost proposal sourced entirely from multiple-choice exams; excluding those
        days left 0 boost proposals. See archive/2026-07-23/README.md.
        """
        if self.opt is None or coherence is None:
            return  # coherence is the one signal every turn must have
        if is_benchmark:
            return  # exam traffic is not evidence about conversational routing
        # tension (Xi) may be None: it is variance ACROSS perspectives, so
        # single-adapter turns have none to report. Those turns ARE recorded —
        # requiring Xi silently restricted the optimizer to multi-perspective
        # turns only (5 of 12 in a real 2026-07-23 conversation), biasing the
        # sample it learns routing from. The reward renormalizes without it.

        productivity_is_proxy = render_fidelity is None
        productivity = 0.5 if productivity_is_proxy else float(render_fidelity)
        tension_val = None if tension is None else float(tension)

        n_hist = len(self.opt.history)
        try:
            self.opt.record_signal(self._QSignal(
                timestamp=time.time(), adapter=adapter or "unknown",
                coherence=float(coherence), tension=tension_val,
                productivity=productivity, response_length=int(response_length),
                multi_perspective=bool(multi_perspective),
                # user_continued omitted (None): engagement is only knowable on the
                # NEXT turn. Passing True was a constant +0.10 on every score.
                user_continued=None,
            ))
        except Exception:
            return

        # Any NEW proposed adjustment this turn?
        new_steps = self.opt.history[n_hist:]
        self._log_turn(adapter, coherence, tension_val, productivity,
                       productivity_is_proxy, new_steps)
        if self._telemetry is not None:
            self._telemetry.record(
                mode="live" if self.live else "shadow",
                adapter=adapter,
                coherence=float(coherence),
                # telemetry schema wants a number; -1.0 sentinel = not measured
                tension=(-1.0 if tension_val is None else tension_val),
                productivity=float(productivity),
                response_length=int(response_length),
                multi_perspective=bool(multi_perspective),
                proposed_count=len(new_steps),
                applied=self.live,
            )
        self._persist()

    def get_adapter_boost(self, adapter: str) -> float:
        """Router reads this. In shadow mode it always returns 0.0 (applies nothing);
        live mode returns the tuned boost."""
        if not self.live or self.opt is None:
            return 0.0
        return self.opt.get_adapter_boost(adapter)

    def _log_turn(self, adapter, coherence, tension, productivity,
                  productivity_is_proxy, new_steps) -> None:
        try:
            _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            rec = {
                "ts": time.time(),
                "mode": "live" if self.live else "shadow",
                "adapter": adapter,
                "signals": {
                    "coherence": round(float(coherence), 4),   # measured
                    # tension is null (not 0.0) on single-adapter turns — there is
                    # no cross-perspective variance to measure. Omitted from the
                    # reward; weights renormalize.
                    "tension": None if tension is None else round(float(tension), 4),
                    "tension_measured": tension is not None,
                    "productivity": round(float(productivity), 4),
                    "productivity_is_placeholder": productivity_is_proxy,
                    # Omitted from the reward entirely (weights renormalized),
                    # rather than fabricated as True and silently scored.
                    "user_continued_measured": False,
                },
                "proposed_adjustments": [
                    {"param": s.parameter, "old": round(s.old_value, 4),
                     "new": round(s.new_value, 4), "reason": s.reason}
                    for s in new_steps
                ],
                "applied": self.live,
            }
            with _LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass  # logging must never break a turn

    def _persist(self) -> None:
        try:
            _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _STATE_PATH.write_text(
                json.dumps(self.opt.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass


# Process-wide singleton (created lazily so import is cheap/safe)
_INSTANCE: Optional[ShadowOptimizer] = None


def get_shadow_optimizer() -> Optional[ShadowOptimizer]:
    global _INSTANCE
    if _INSTANCE is None:
        try:
            _INSTANCE = ShadowOptimizer()
        except Exception:
            _INSTANCE = None
    return _INSTANCE
