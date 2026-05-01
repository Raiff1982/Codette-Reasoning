#!/usr/bin/env python3
"""Codette Web Server — Zero-Dependency Local AI Chat

Pure Python stdlib HTTP server with SSE streaming.
No Flask, no FastAPI, no npm, no node — just Python.

Usage:
    python codette_server.py                    # Start on port 7860
    python codette_server.py --port 8080        # Custom port
    python codette_server.py --no-browser       # Don't auto-open browser

Architecture:
    - http.server for static files + REST API
    - Server-Sent Events (SSE) for streaming responses
    - Threading for background model loading/inference
    - CodetteOrchestrator for routing + generation
    - CodetteSession for Cocoon-backed memory
"""

import os, sys, json, time, threading, queue, argparse, webbrowser, traceback, re, uuid
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from io import BytesIO
import email, email.policy

# ---------------------------------------------------------------------------
# Minimal multipart/form-data parser — replaces the removed `cgi` module
# (removed in Python 3.13).  Provides the same interface used in this file:
#   form.getfirst(key, default) → str | None
#   key in form
#   form[key] → FieldItem | list[FieldItem]
#   FieldItem.filename, FieldItem.file.read()
# ---------------------------------------------------------------------------
class _FieldItem:
    """Represents one multipart field (file or text)."""
    def __init__(self, name: str, value: bytes, filename: str | None = None):
        self.name = name
        self._value = value
        self.filename = filename
        self.file = BytesIO(value)

    def getvalue(self) -> bytes:
        return self._value


class _FieldStorage:
    """Drop-in replacement for cgi.FieldStorage."""

    def __init__(self, fp: BytesIO, headers, environ: dict):
        self._fields: dict[str, list[_FieldItem]] = {}
        content_type = environ.get("CONTENT_TYPE", "")
        body = fp.read()
        # Build a fake email message so email.parser can split the parts
        msg_bytes = (
            f"Content-Type: {content_type}\r\n\r\n".encode() + body
        )
        msg = email.message_from_bytes(msg_bytes, policy=email.policy.compat32)
        if msg.get_content_maintype() != "multipart":
            return
        for part in msg.get_payload():
            if not isinstance(part, email.message.Message):
                continue
            disp = part.get("Content-Disposition", "")
            # Extract name and filename from Content-Disposition
            name = None
            filename = None
            for chunk in disp.split(";"):
                chunk = chunk.strip()
                if chunk.startswith("name="):
                    name = chunk[5:].strip('"')
                elif chunk.startswith("filename="):
                    filename = chunk[9:].strip('"')
            if name is None:
                continue
            payload = part.get_payload(decode=True) or b""
            item = _FieldItem(name, payload, filename)
            self._fields.setdefault(name, []).append(item)

    def __contains__(self, key: str) -> bool:
        return key in self._fields

    def __getitem__(self, key: str):
        items = self._fields[key]
        return items if len(items) > 1 else items[0]

    def getfirst(self, key: str, default=None):
        items = self._fields.get(key)
        if not items:
            return default
        val = items[0].getvalue()
        return val.decode("utf-8", errors="replace") if isinstance(val, bytes) else val


from runtime_env import bootstrap_environment, resolve_model_path
from web_search import query_benefits_from_web_research, query_requests_web_research

bootstrap_environment()
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from codette_session import (
    CodetteSession, SessionStore, ADAPTER_COLORS, AGENT_NAMES, is_ephemeral_response_constraint_text
)

# Lazy import orchestrator (heavy — loads llama_cpp)
_orchestrator = None
_orchestrator_lock = threading.Lock()
_inference_semaphore = threading.Semaphore(1)  # Limit to 1 concurrent inference (llama.cpp can't parallelize)
_orchestrator_status = {"state": "idle", "message": "Not loaded"}
_orchestrator_status_lock = threading.Lock()  # Protect _orchestrator_status from race conditions
_load_error = None

# Phase 6 bridge (optional, wraps orchestrator)
_forge_bridge = None
_use_phase6 = True  # ENABLED: Foundation restoration (memory kernel + stability field) wrapped in ForgeEngine + Phase 7 routing

# Current session
_session: CodetteSession = None
_session_store: SessionStore = None
_session_lock = threading.Lock()

# Identity persistence (Challenge 3: user recognition & relationship continuity)
_identity_anchor = None
try:
    from identity_anchor import IdentityAnchor
    _identity_anchor = IdentityAnchor()
    print(f"  Identity anchor loaded ({len(_identity_anchor.identities)} known identities)")
except Exception as e:
    print(f"  Identity anchor unavailable: {e}")

# Behavior Governor (Executive Controller v2)
_behavior_governor = None
try:
    from reasoning_forge.behavior_governor import BehaviorGovernor
    _behavior_governor = BehaviorGovernor(identity_anchor=_identity_anchor)
    print("  Behavior Governor loaded (identity + memory + cognitive load governance)")
except Exception as e:
    print(f"  Behavior Governor unavailable: {e}")

# Unified Memory (SQLite + FTS5 — replaces CognitionCocooner for recall)
_unified_memory = None
try:
    from reasoning_forge.unified_memory import UnifiedMemory
    _unified_memory = UnifiedMemory()
    print(f"  Unified Memory loaded ({_unified_memory._total_stored} cocoons, FTS5 active)")
except Exception as e:
    print(f"  Unified Memory unavailable (falling back to CognitionCocooner): {e}")

_memory_weighting = None


def _get_memory_weighting():
    """Lazily initialize memory weighting against the active unified memory store."""
    global _memory_weighting
    if _memory_weighting is not None:
        return _memory_weighting
    if not _unified_memory:
        return None

    try:
        from reasoning_forge.memory_weighting import MemoryWeighting
        _memory_weighting = MemoryWeighting(_unified_memory, update_interval_hours=0.1)
        print("  Memory weighting loaded (unified cocoon feedback active)")
    except Exception as e:
        print(f"  Memory weighting unavailable: {e}")
        _memory_weighting = None
    return _memory_weighting


def _analyze_response_reliability(response_text: str, adapter_name: str, domain: str = "general") -> dict:
    """Run post-generation reliability analysis over the final response text."""
    analysis = {
        "response_confidence": 0.5,
        "hallucination_confidence": 1.0,
        "hallucination_detected": False,
        "hallucination_signals": [],
        "hallucination_recommendation": "CONTINUE",
        "low_confidence_claims": [],
        "mean_token_confidence": 0.5,
    }
    if not response_text.strip():
        return analysis

    try:
        from reasoning_forge.hallucination_guard import HallucinationGuard
        guard = HallucinationGuard()
        detection = guard.scan_chunk(response_text, domain=domain or "general")
        analysis.update({
            "hallucination_confidence": round(detection.confidence_score, 3),
            "hallucination_detected": bool(detection.is_hallucination),
            "hallucination_signals": detection.signals[:5],
            "hallucination_recommendation": detection.recommendation,
        })
    except Exception as e:
        analysis["hallucination_signals"] = [f"hallucination_guard_unavailable: {e}"]

    try:
        from reasoning_forge.token_confidence import TokenConfidenceEngine
        scorer = TokenConfidenceEngine(living_memory=_unified_memory)
        token_report = scorer.score_tokens(response_text, adapter_name or "base")
        mean_token_conf = (
            sum(token_report.token_scores) / max(len(token_report.token_scores), 1)
        )
        low_claims = sorted(token_report.claims, key=lambda claim: claim.confidence)[:3]
        analysis.update({
            "mean_token_confidence": round(mean_token_conf, 3),
            "low_confidence_claims": [
                {
                    "text": claim.text[:180],
                    "confidence": round(claim.confidence, 3),
                }
                for claim in low_claims
                if claim.text.strip()
            ],
        })
    except Exception as e:
        analysis["low_confidence_claims"] = [{"text": f"token_confidence_unavailable: {e}", "confidence": 0.0}]

    combined_confidence = analysis["mean_token_confidence"] * analysis["hallucination_confidence"]
    analysis["response_confidence"] = round(max(0.0, min(1.0, combined_confidence)), 3)
    return analysis


def _build_trust_tags(result: dict, memory_context_summary: dict) -> list[str]:
    """Summarize why a response should be trusted, or where caution is needed."""
    tags = []
    response_confidence = float(result.get("response_confidence", 0.5) or 0.5)
    confidence_analysis = result.get("confidence_analysis", {}) or {}

    if response_confidence >= 0.78:
        tags.append("stable")
    elif response_confidence < 0.45:
        tags.append("low-verification")

    if memory_context_summary.get("recalled_cocoons_used") or memory_context_summary.get("session_markers_used"):
        tags.append("memory-backed")
    if memory_context_summary.get("value_analyses_used"):
        tags.append("frontier-informed")
    if memory_context_summary.get("web_research_used"):
        tags.append("web-cited")
    if result.get("tools_used"):
        tags.append("tool-assisted")
    if confidence_analysis.get("hallucination_detected"):
        tags.append("hallucination-risk")
    elif confidence_analysis.get("hallucination_confidence", 1.0) >= 0.85:
        tags.append("grounded")

    seen = set()
    ordered = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return ordered[:5]


def _summarize_web_research(results) -> str:
    """Format fetched web research into a prompt-safe summary block."""
    if not results:
        return ""
    lines = ["# WEB RESEARCH", "Use these cited current sources when relevant:"]
    for index, result in enumerate(results, start=1):
        title = result.get("title", "Untitled source")
        url = result.get("url", "")
        snippet = (result.get("fetched_text") or result.get("snippet") or "").replace("\n", " ").strip()
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        lines.append(f"{index}. {title} — {url}")
        if snippet:
            lines.append(f"   {snippet}")
    return "\n".join(lines)


def _resolve_web_research_request(query: str, allow_web_search: bool) -> tuple[bool, str]:
    """Resolve whether safe live web research should run for this request."""
    if query_requests_web_research(query):
        return True, "phrase"
    if allow_web_search and query_benefits_from_web_research(query):
        return True, "toggle"
    return False, ""

# Request queue for thread-safe model access
_request_queue = queue.Queue()
_response_queues = {}  # request_id -> queue.Queue
_response_queues_lock = threading.Lock()  # Protect _response_queues from race conditions
_queue_creation_times = {}  # Track when each queue was created for cleanup

# Worker threads for health monitoring
_worker_threads = []
_worker_threads_lock = threading.Lock()


def _next_request_id(prefix: str = "req") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _register_response_queue(prefix: str = "req") -> tuple[str, queue.Queue]:
    req_id = _next_request_id(prefix)
    response_q = queue.Queue()
    with _response_queues_lock:
        _response_queues[req_id] = response_q
        _queue_creation_times[req_id] = time.time()
    return req_id, response_q


def _unregister_response_queue(req_id: str) -> None:
    with _response_queues_lock:
        _response_queues.pop(req_id, None)
        _queue_creation_times.pop(req_id, None)


def _get_response_queue(req_id: str):
    with _response_queues_lock:
        return _response_queues.get(req_id)


def _get_active_session():
    with _session_lock:
        return _session


def _set_active_session(session) -> None:
    global _session
    with _session_lock:
        _session = session


def _get_orchestrator():
    """Lazy-load the orchestrator (first call takes ~60s).

    Set CODETTE_BACKEND=ollama to use Ollama instead of llama_cpp.
    Ollama provides faster inference with proper GPU acceleration.
    """
    global _orchestrator, _orchestrator_status, _load_error, _forge_bridge
    if _orchestrator is not None:
        return _orchestrator

    with _orchestrator_lock:
        if _orchestrator is not None:
            return _orchestrator

        backend = os.environ.get("CODETTE_BACKEND", "llama_cpp").lower()

        # Validate model path exists before attempting load — prevents silent hang
        if backend != "ollama":
            from runtime_env import resolve_model_path
            _model_path = resolve_model_path()
            if not _model_path.exists():
                _load_error = (
                    f"Model file not found: {_model_path}\n"
                    f"Set CODETTE_MODEL_PATH env var or place the GGUF at that location."
                )
                with _orchestrator_status_lock:
                    _orchestrator_status.update({"state": "error", "message": _load_error})
                print(f"  ERROR: {_load_error}")
                return None

        with _orchestrator_status_lock:
            _orchestrator_status.update({"state": "loading", "message": f"Loading Codette model ({backend})..."})
        print(f"\n  Loading CodetteOrchestrator (backend: {backend})...")

        try:
            memory_weighting = _get_memory_weighting()
            if backend == "ollama":
                from ollama_orchestrator import OllamaOrchestrator
                _orchestrator = OllamaOrchestrator(
                    verbose=True,
                    n_ctx=32768,
                    memory_weighting=memory_weighting,
                )
            else:
                from codette_orchestrator import CodetteOrchestrator
                import concurrent.futures as _cf
                # Load with a 5-minute timeout — llama_cpp can hang indefinitely
                # on corrupted GGUF files without raising an exception.
                with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
                    _fut = _pool.submit(
                        CodetteOrchestrator,
                        verbose=True,
                        n_ctx=32768,
                        memory_weighting=memory_weighting,
                    )
                    try:
                        _orchestrator = _fut.result(timeout=300)
                    except _cf.TimeoutError:
                        raise RuntimeError(
                            "Model load timed out after 5 minutes — "
                            "the GGUF may be corrupted or the system is out of memory."
                        )

            with _orchestrator_status_lock:
                _orchestrator_status.update({
                    "state": "ready",
                    "message": f"Ready — {len(_orchestrator.available_adapters)} adapters ({backend})",
                    "adapters": _orchestrator.available_adapters,
                    "backend": backend,
                })
            print(f"  Orchestrator ready ({backend}): {_orchestrator.available_adapters}")

            # Initialize Phase 6 bridge with Phase 7 routing (wraps orchestrator with ForgeEngine + Executive Controller)
            print(f"  [DEBUG] _use_phase6 = {_use_phase6}")
            if _use_phase6:
                try:
                    print(f"  [DEBUG] Importing CodetteForgeBridge...")
                    from codette_forge_bridge import CodetteForgeBridge
                    print(f"  [DEBUG] Creating bridge instance...")
                    _forge_bridge = CodetteForgeBridge(_orchestrator, use_phase6=True, use_phase7=True, verbose=True, health_check_fn=_run_health_check)
                    print(f"  Phase 6 bridge initialized")
                    print(f"  Phase 7 Executive Controller initialized")
                    # Add memory count from forge kernel
                    mem_count = 0
                    if hasattr(_forge_bridge, 'forge') and hasattr(_forge_bridge.forge, 'memory_kernel') and _forge_bridge.forge.memory_kernel:
                        mem_count = len(_forge_bridge.forge.memory_kernel.memories)
                    with _orchestrator_status_lock:
                        _orchestrator_status.update({"phase6": "enabled", "phase7": "enabled", "memory_count": mem_count})
                except Exception as e:
                    print(f"  Phase 6/7 bridge failed (using lightweight routing): {e}")
                    traceback.print_exc()
                    with _orchestrator_status_lock:
                        _orchestrator_status.update({"phase6": "disabled", "phase7": "disabled"})
            else:
                print(f"  [DEBUG] Phase 6 disabled (_use_phase6=False)")

            return _orchestrator
        except Exception as e:
            _load_error = str(e)
            with _orchestrator_status_lock:
                _orchestrator_status.update({"state": "error", "message": f"Load failed: {e}"})
            print(f"  ERROR loading orchestrator: {e}")
            traceback.print_exc()
            return None


def _cleanup_orphaned_queues():
    """Periodically clean up response queues that are older than 30 minutes.

    This prevents memory leaks from accumulating abandoned request queues.
    Timeout must exceed max handler timeout (1200s) to avoid dropping
    responses that the handler is still actively waiting for.
    """
    while True:
        try:
            time.sleep(120)  # Run cleanup every 2 minutes
            now = time.time()

            with _response_queues_lock:
                # Find queues older than 30 minutes (1800 seconds)
                orphaned = []
                for req_id, creation_time in list(_queue_creation_times.items()):
                    if now - creation_time > 1800:
                        orphaned.append(req_id)

                # Remove orphaned queues
                for req_id in orphaned:
                    _response_queues.pop(req_id, None)
                    _queue_creation_times.pop(req_id, None)

                if orphaned:
                    print(f"  Cleaned up {len(orphaned)} orphaned response queues")
        except Exception as e:
            print(f"  WARNING: Cleanup thread error: {e}")


def _monitor_worker_health():
    """Monitor worker threads and restart any that have died.

    This ensures the system remains responsive even if a worker crashes.
    """
    while True:
        try:
            time.sleep(5)  # Check every 5 seconds

            with _worker_threads_lock:
                # Check each worker thread
                alive_workers = []
                dead_workers = []

                for i, worker in enumerate(_worker_threads):
                    if worker.is_alive():
                        alive_workers.append((i, worker))
                    else:
                        dead_workers.append(i)

                # Log and restart any dead workers
                if dead_workers:
                    print(f"  WARNING: Detected {len(dead_workers)} dead worker(s): {dead_workers}")
                    for i in dead_workers:
                        print(f"  Restarting worker thread {i}...")
                        new_worker = threading.Thread(target=_worker_thread, daemon=True, name=f"worker-{i}")
                        new_worker.start()
                        _worker_threads[i] = new_worker
                    print(f"  Worker threads restarted successfully")

                # Log current work queue status periodically
                work_queue_size = _request_queue.qsize()
                if work_queue_size > 0:
                    print(f"  Worker status: {len(alive_workers)} alive, {len(_response_queues)} pending requests, {work_queue_size} queued")

        except Exception as e:
            print(f"  WARNING: Worker health monitor error: {e}")


def _run_health_check():
    """Run a real self-diagnostic across all Codette subsystems.

    Returns actual system state — not generated text about health,
    but measured values from every component.
    """
    report = {
        "timestamp": time.time(),
        "overall": "unknown",
        "systems": {},
        "warnings": [],
        "errors": [],
    }

    checks_passed = 0
    checks_total = 0

    # 1. Model / Orchestrator
    checks_total += 1
    if _orchestrator:
        report["systems"]["model"] = {
            "status": "OK",
            "adapters_loaded": len(getattr(_orchestrator, 'available_adapters', [])),
            "adapters": getattr(_orchestrator, 'available_adapters', []),
            "base_model": resolve_model_path().stem,
        }
        checks_passed += 1
    else:
        report["systems"]["model"] = {"status": "NOT LOADED"}
        report["errors"].append("Model not loaded")

    # 2. Phase 6 / ForgeEngine
    checks_total += 1
    if _forge_bridge and _forge_bridge.use_phase6:
        forge = _forge_bridge.forge
        p6 = {"status": "OK", "components": {}}

        # Memory kernel
        if hasattr(forge, 'memory_kernel') and forge.memory_kernel:
            mem_count = len(forge.memory_kernel.memories)
            p6["components"]["memory_kernel"] = {"status": "OK", "memories": mem_count}
        else:
            p6["components"]["memory_kernel"] = {"status": "MISSING"}
            report["warnings"].append("Memory kernel not initialized")

        # Stability field
        # Check both possible attribute names
        stability = getattr(forge, 'cocoon_stability', None) or getattr(forge, 'stability_field', None)
        if stability:
            p6["components"]["stability_field"] = {"status": "OK", "type": type(stability).__name__}
        else:
            p6["components"]["stability_field"] = {"status": "MISSING"}

        # Colleen conscience
        if hasattr(forge, 'colleen') and forge.colleen:
            p6["components"]["colleen_conscience"] = {"status": "OK"}
        else:
            p6["components"]["colleen_conscience"] = {"status": "MISSING"}
            report["warnings"].append("Colleen conscience not loaded")

        # Guardian spindle
        if hasattr(forge, 'guardian') and forge.guardian:
            p6["components"]["guardian_spindle"] = {"status": "OK"}
        else:
            p6["components"]["guardian_spindle"] = {"status": "MISSING"}

        # Ethical governance
        if hasattr(forge, 'ethical_governance') and forge.ethical_governance:
            eg = forge.ethical_governance
            audit_count = len(getattr(eg, 'audit_log', []))
            queries_blocked = sum(1 for entry in getattr(eg, 'audit_log', []) if entry.get('action') == 'blocked')
            p6["components"]["ethical_governance"] = {
                "status": "OK",
                "audit_entries": audit_count,
                "queries_blocked": queries_blocked,
                "detection_rules": len(getattr(eg, 'harmful_patterns', [])) + len(getattr(eg, 'bias_patterns', [])),
            }
        else:
            p6["components"]["ethical_governance"] = {"status": "MISSING"}
            report["warnings"].append("Ethical governance not loaded")

        # CognitionCocooner
        if hasattr(forge, 'cocooner') and forge.cocooner:
            cocoon_count = len(getattr(forge.cocooner, 'cocoons', {}))
            p6["components"]["cognition_cocooner"] = {
                "status": "OK",
                "stored_cocoons": cocoon_count,
            }
        else:
            p6["components"]["cognition_cocooner"] = {"status": "MISSING"}

        # Self-awareness (tier2 bridge)
        if hasattr(forge, 'tier2_bridge') and forge.tier2_bridge:
            p6["components"]["tier2_bridge"] = {"status": "OK"}
        else:
            p6["components"]["tier2_bridge"] = {"status": "MISSING"}

        report["systems"]["phase6_forge"] = p6
        checks_passed += 1
    else:
        report["systems"]["phase6_forge"] = {"status": "DISABLED"}
        report["warnings"].append("Phase 6 ForgeEngine not active")

    # 3. Phase 7 / Executive Controller
    checks_total += 1
    if _forge_bridge and _forge_bridge.use_phase7 and _forge_bridge.executive_controller:
        report["systems"]["phase7_executive"] = {"status": "OK"}
        checks_passed += 1
    else:
        report["systems"]["phase7_executive"] = {"status": "DISABLED"}
        report["warnings"].append("Phase 7 Executive Controller not active")

    # 4. Session / Cocoon subsystems
    checks_total += 1
    if _session:
        try:
            sess = {
                "status": "OK",
                "session_id": getattr(_session, 'session_id', 'unknown'),
                "message_count": len(getattr(_session, 'messages', [])),
                "subsystems": {},
            }
            sub_names = [
                ("spiderweb", "QuantumSpiderweb"),
                ("metrics_engine", "EpistemicMetrics"),
                ("cocoon_sync", "CocoonSync"),
                ("dream_reweaver", "DreamReweaver"),
                ("optimizer", "QuantumOptimizer"),
                ("memory_kernel", "LivingMemory"),
                ("guardian", "CodetteGuardian"),
                ("resonance_engine", "ResonantContinuity"),
                ("aegis", "AEGIS"),
                ("nexus", "NexusSignalEngine"),
            ]
            for attr, label in sub_names:
                obj = getattr(_session, attr, None)
                sess["subsystems"][label] = "OK" if obj else "MISSING"

            # Spiderweb metrics (safely)
            sw = getattr(_session, 'spiderweb', None)
            if sw:
                try:
                    sess["spiderweb_metrics"] = {
                        "phase_coherence": sw.phase_coherence() if hasattr(sw, 'phase_coherence') else 0,
                        "entropy": sw.shannon_entropy() if hasattr(sw, 'shannon_entropy') else 0,
                        "decoherence_rate": sw.decoherence_rate() if hasattr(sw, 'decoherence_rate') else 0,
                        "node_count": len(getattr(sw, 'nodes', [])),
                        "attractor_count": len(getattr(_session, 'attractors', [])),
                        "glyph_count": len(getattr(_session, 'glyphs', [])),
                    }
                except Exception:
                    sess["spiderweb_metrics"] = {"error": "failed to read"}

            # Coherence/tension history (safely)
            ch = getattr(_session, 'coherence_history', [])
            th = getattr(_session, 'tension_history', [])
            sess["coherence_entries"] = len(ch)
            sess["tension_entries"] = len(th)
            sess["current_coherence"] = ch[-1] if ch else None
            sess["current_tension"] = th[-1] if th else None
            sess["perspective_usage"] = dict(getattr(_session, 'perspective_usage', {}))

            report["systems"]["session"] = sess
            checks_passed += 1
        except Exception as e:
            report["systems"]["session"] = {"status": "ERROR", "detail": str(e)}
            report["warnings"].append(f"Session check failed: {e}")
    else:
        report["systems"]["session"] = {"status": "NOT INITIALIZED"}
        report["errors"].append("No active session")

    # 5. Self-correction system
    checks_total += 1
    try:
        from self_correction import BehaviorMemory  # noqa
        bm = BehaviorMemory()
        report["systems"]["self_correction"] = {
            "status": "OK",
            "behavior_lessons": len(getattr(bm, 'lessons', [])),
            "permanent_locks": 4,
        }
        checks_passed += 1
    except ImportError:
        report["systems"]["self_correction"] = {"status": "NOT AVAILABLE"}
        report["warnings"].append("Self-correction module not importable")

    # 6. Worker threads
    checks_total += 1
    with _worker_threads_lock:
        alive = sum(1 for w in _worker_threads if w.is_alive())
        total = len(_worker_threads)
    report["systems"]["worker_threads"] = {
        "status": "OK" if alive == total else "DEGRADED",
        "alive": alive,
        "total": total,
        "pending_requests": _request_queue.qsize(),
    }
    if alive == total:
        checks_passed += 1
    else:
        report["warnings"].append(f"{total - alive} worker thread(s) dead")

    # 7. Inference semaphore
    checks_total += 1
    # _value is internal but useful for diagnostics
    sem_available = getattr(_inference_semaphore, '_value', 1)
    report["systems"]["inference_lock"] = {
        "status": "OK" if sem_available > 0 else "BUSY",
        "available": sem_available > 0,
    }
    checks_passed += 1

    # 8. Substrate awareness (real-time system pressure)
    checks_total += 1
    if _forge_bridge and hasattr(_forge_bridge, 'substrate_monitor') and _forge_bridge.substrate_monitor:
        try:
            substrate = _forge_bridge.substrate_monitor.snapshot()
            report["systems"]["substrate"] = {
                "status": "OK",
                "pressure": substrate["pressure"],
                "level": substrate["level"],
                "memory_pct": substrate["memory_pct"],
                "memory_available_gb": substrate["memory_available_gb"],
                "cpu_pct": substrate["cpu_pct"],
                "process_memory_gb": substrate["process_memory_gb"],
                "inference_avg_ms": substrate["inference_avg_ms"],
                "trend": _forge_bridge.substrate_monitor.trend(),
                "adapter_health": _forge_bridge.substrate_monitor.get_adapter_health(),
            }
            checks_passed += 1
        except Exception as e:
            report["systems"]["substrate"] = {"status": "ERROR", "detail": str(e)}
            report["warnings"].append(f"Substrate monitor error: {e}")
    else:
        report["systems"]["substrate"] = {"status": "NOT AVAILABLE"}
        report["warnings"].append("Substrate-aware cognition not initialized")

    # 9. Cocoon Introspection (memory pattern analysis)
    checks_total += 1
    try:
        from cocoon_introspection import CocoonIntrospectionEngine
        intro_engine = CocoonIntrospectionEngine()
        dom = intro_engine.adapter_dominance()
        report["systems"]["introspection"] = {
            "status": "OK",
            "reasoning_cocoons": dom.get("total_responses", 0),
            "dominant_adapter": dom.get("dominant"),
            "dominance_ratio": dom.get("ratio", 0),
            "balanced": dom.get("balanced", True),
        }
        checks_passed += 1
    except Exception as e:
        report["systems"]["introspection"] = {"status": "ERROR", "detail": str(e)}
        report["warnings"].append(f"Cocoon introspection error: {e}")

    # Overall grade
    if checks_passed == checks_total and not report["errors"]:
        report["overall"] = "HEALTHY"
    elif report["errors"]:
        report["overall"] = "CRITICAL"
    elif checks_passed >= checks_total - 1:
        report["overall"] = "GOOD"
    else:
        report["overall"] = "DEGRADED"

    report["checks_passed"] = checks_passed
    report["checks_total"] = checks_total
    report["score"] = f"{checks_passed}/{checks_total}"

    return report


def _worker_thread():
    """Background worker that processes inference requests."""
    # Session management is active via _get_active_session() at line 1029
    # Manages continuity summaries, cocoon updates, epistemic tracking

    while True:
        try:
            request = _request_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        if request is None:
            break  # Shutdown signal

        req_id = request["id"]

        # Get response queue with thread lock (prevent race condition)
        response_q = _get_response_queue(req_id)

        if not response_q:
            print(f"  WARNING: Orphaned request {req_id} (response queue missing)")
            continue

        try:
            orch = _get_orchestrator()
            if orch is None:
                try:
                    response_q.put({"error": _load_error or "Model failed to load"})
                except (queue.Full, RuntimeError) as e:
                    print(f"  ERROR: Failed to queue error response: {e}")
                continue

            query = request["query"]
            query_lower = query.lower().strip()
            adapter = request.get("adapter")  # None = auto-route
            max_adapters = request.get("max_adapters", 2)
            web_search_trigger = request.get("web_search_trigger", "")

            # ── SELF-INTROSPECTION INTERCEPT ──
            # When user asks about self-reflection, patterns, or what she's noticed,
            # run real cocoon analysis instead of LLM-generated text about reflection
            _introspection_patterns = [
                r"\bself[\s-]?reflection\b",
                r"\bintrospect(?:ion)?\b",
                r"\bwhat have you (?:noticed|learned) about yourself\b",
                r"\bwhat do you notice about yourself\b",
                r"\banalyze your (?:own|response) patterns\b",
                r"\bcocoon (?:analysis|patterns)\b",
                r"\badapter (?:frequency|dominance)\b",
                r"\byour reasoning history\b",
                r"\byour emotional patterns\b",
                r"\byour response patterns\b",
            ]
            if any(re.search(pattern, query, re.IGNORECASE) for pattern in _introspection_patterns):
                print(f"  [WORKER] Intercepted introspection query — running real cocoon analysis", flush=True)

                try:
                    response_q.put({"event": "thinking", "adapter": "introspection"})
                except (queue.Full, RuntimeError):
                    pass

                try:
                    from cocoon_introspection import CocoonIntrospectionEngine
                    engine = CocoonIntrospectionEngine()
                    report = engine.format_introspection()
                except Exception as e:
                    report = f"**Introspection Error** — Could not analyze cocoon history: {e}"

                try:
                    response_q.put({
                        "event": "complete",
                        "response": report,
                        "adapter": "introspection",
                        "confidence": 1.0,
                        "reasoning": "Real cocoon analysis — not generated text",
                        "tokens": 0,
                        "time": 0.01,
                        "complexity": "SYSTEM",
                        "domain": "introspection",
                        "ethical_checks": 0,
                    })
                except (queue.Full, RuntimeError):
                    pass
                continue

            # ── SELF-DIAGNOSTIC INTERCEPT ──
            # When user asks for a health/system check, run the REAL diagnostic
            # instead of letting the model generate text about it
            _health_triggers = [
                "health check",
                "system health",
                "system health check",
                "self diagnostic",
                "self-diagnostic",
                "systems check",
                "system check",
                "run diagnostic",
                "run a diagnostic",
                "diagnostic report",
                "check your systems",
                "check all systems",
                "how are your systems",
                "self systems health",
                "system status",
                "system status report",
            ]
            if any(trigger in query_lower for trigger in _health_triggers):
                print(f"  [WORKER] Intercepted health check query — running real diagnostic", flush=True)

                # Must send thinking event first (POST handler expects it)
                try:
                    response_q.put({"event": "thinking", "adapter": "self_diagnostic"})
                except (queue.Full, RuntimeError):
                    pass

                try:
                    health = _run_health_check()
                except Exception as e:
                    health = {"overall": "ERROR", "score": "0/0", "systems": {}, "warnings": [], "errors": [str(e)]}

                # Format the real data into a readable response
                lines = []
                lines.append(f"**Self-Diagnostic Report** — Overall: **{health['overall']}** ({health['score']} checks passed)\n")

                for sys_name, sys_data in health.get("systems", {}).items():
                    status = sys_data.get("status", "?")
                    icon = "+" if status in ("OK", "HEALTHY") else ("-" if status == "MISSING" else "!")
                    nice_name = sys_name.replace("_", " ").title()
                    lines.append(f"[{icon}] **{nice_name}**: {status}")

                    # Show key details per subsystem
                    if sys_name == "model":
                        lines.append(f"    Adapters loaded: {sys_data.get('adapters_loaded', '?')}")
                    elif sys_name == "phase6_forge":
                        for comp_name, comp_data in sys_data.get("components", {}).items():
                            comp_status = comp_data if isinstance(comp_data, str) else comp_data.get("status", "?")
                            comp_nice = comp_name.replace("_", " ").title()
                            detail_parts = []
                            if isinstance(comp_data, dict):
                                for k, v in comp_data.items():
                                    if k != "status":
                                        detail_parts.append(f"{k}={v}")
                            detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
                            lines.append(f"    {comp_nice}: {comp_status}{detail}")
                    elif sys_name == "session":
                        lines.append(f"    Messages: {sys_data.get('message_count', 0)}")
                        lines.append(f"    Coherence entries: {sys_data.get('coherence_entries', 0)}")
                        lines.append(f"    Tension entries: {sys_data.get('tension_entries', 0)}")
                        if "spiderweb_metrics" in sys_data:
                            sw = sys_data["spiderweb_metrics"]
                            lines.append(f"    Spiderweb: coherence={sw.get('phase_coherence', 0):.4f}, entropy={sw.get('entropy', 0):.4f}, nodes={sw.get('node_count', 0)}, attractors={sw.get('attractor_count', 0)}")
                        if sys_data.get("perspective_usage"):
                            usage = sys_data["perspective_usage"]
                            lines.append(f"    Perspective usage: {dict(usage)}")
                        for sub_name, sub_status in sys_data.get("subsystems", {}).items():
                            sub_icon = "+" if sub_status == "OK" else "-"
                            lines.append(f"    [{sub_icon}] {sub_name}: {sub_status}")
                    elif sys_name == "self_correction":
                        lines.append(f"    Behavior lessons: {sys_data.get('behavior_lessons', 0)}")
                        lines.append(f"    Permanent locks: {sys_data.get('permanent_locks', 0)}")
                    elif sys_name == "worker_threads":
                        lines.append(f"    Alive: {sys_data.get('alive', 0)}/{sys_data.get('total', 0)}")
                        lines.append(f"    Pending requests: {sys_data.get('pending_requests', 0)}")
                    elif sys_name == "substrate":
                        lines.append(f"    Pressure: {sys_data.get('pressure', 0):.3f} ({sys_data.get('level', '?')})")
                        lines.append(f"    Memory: {sys_data.get('memory_pct', 0)}% used, {sys_data.get('memory_available_gb', 0)}GB available")
                        lines.append(f"    Process: {sys_data.get('process_memory_gb', 0)}GB RSS")
                        lines.append(f"    CPU: {sys_data.get('cpu_pct', 0)}%")
                        lines.append(f"    Inference avg: {sys_data.get('inference_avg_ms', 0):.0f}ms")
                        lines.append(f"    Trend: {sys_data.get('trend', '?')}")
                        ah = sys_data.get('adapter_health', {})
                        if ah:
                            lines.append(f"    Adapter health: {ah}")
                    elif sys_name == "introspection":
                        lines.append(f"    Reasoning cocoons: {sys_data.get('reasoning_cocoons', 0)}")
                        lines.append(f"    Dominant adapter: {sys_data.get('dominant_adapter', 'none')}")
                        lines.append(f"    Dominance ratio: {sys_data.get('dominance_ratio', 0):.1%}")
                        lines.append(f"    Balanced: {'Yes' if sys_data.get('balanced', True) else 'No — may be over-relying'}")

                if health.get("warnings"):
                    lines.append(f"\nWarnings: {', '.join(health['warnings'])}")
                if health.get("errors"):
                    lines.append(f"\nErrors: {', '.join(health['errors'])}")

                diag_response = "\n".join(lines)

                try:
                    response_q.put({
                        "event": "complete",
                        "response": diag_response,
                        "adapter": "self_diagnostic",
                        "confidence": 1.0,
                        "reasoning": "Real self-diagnostic — not generated text",
                        "tokens": 0,
                        "time": 0.01,
                        "complexity": "SYSTEM",
                        "domain": "self_diagnostic",
                        "ethical_checks": 0,
                        "memory_count": health.get("systems", {}).get("phase6_forge", {}).get("components", {}).get("cognition_cocooner", {}).get("stored_cocoons", 0),
                    })
                except (queue.Full, RuntimeError):
                    pass
                continue

            # ── ARTIST QUERY INTERCEPT (hallucination prevention) ──
            # Only fires when query is CLEARLY about a music artist/band/album.
            # Must have explicit music context to avoid false positives on casual conversation.
            _music_context_words = {'album', 'song', 'songs', 'band', 'artist', 'singer',
                                    'discography', 'music', 'genre', 'tour', 'concert',
                                    'track', 'release', 'record', 'label', 'lyrics'}
            has_music_context = any(w in query_lower.split() for w in _music_context_words)
            _artist_patterns = [
                r'\b(who is|tell me about|what do you know about)\b.*\b(artist|singer|band|musician)\b',
                r'\b(album|discography|songs? by|music by)\s+[A-Z]',
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b.+\b(album|song|band|artist|singer|discography)\b',
            ]
            is_artist_query = has_music_context and any(re.search(pattern, query, re.IGNORECASE) for pattern in _artist_patterns)

            if is_artist_query:
                print(f"  [WORKER] Intercepted artist query — routing to uncertainty response", flush=True)
                artist_response = (
                    "I don't have reliable information about specific artists in my training data. Rather than guess or hallucinate details, I'd recommend checking:\n\n"
                    "- **Spotify** — artist bio, discography, listening stats\n"
                    "- **Wikipedia** — career history, notable works\n"
                    "- **Bandcamp** — independent artists, recent releases\n"
                    "- **Official websites** — accurate info straight from the source\n\n"
                    "**What I CAN help with instead:**\n"
                    "- Music production techniques for their genre/style\n"
                    "- Music theory and arrangement analysis\n"
                    "- Creating music inspired by similar vibes\n"
                    "- Sound design for that aesthetic\n\n"
                    "If you describe their music or share a link, I can help you create inspired work or understand the production choices."
                )
                try:
                    response_q.put({"event": "thinking", "adapter": "uncertainty_aware"})
                except (queue.Full, RuntimeError):
                    pass
                try:
                    response_q.put({
                        "event": "complete",
                        "response": artist_response,
                        "adapter": "uncertainty_aware",
                        "confidence": 1.0,
                        "reasoning": "Honest uncertainty > hallucination. User can verify via authoritative sources.",
                        "tokens": 0,
                        "time": 0.01,
                        "complexity": "SIMPLE",
                        "domain": "music",
                        "ethical_checks": 1,
                    })
                except (queue.Full, RuntimeError):
                    pass
                continue

            # Send "thinking" event
            try:
                response_q.put({"event": "thinking", "adapter": adapter or "auto"})
            except (queue.Full, RuntimeError):
                continue

            # Route and generate — limit to 1 concurrent inference to avoid memory exhaustion
            # Add timeout to prevent deadlock if inference gets stuck
            acquired = _inference_semaphore.acquire(timeout=120)
            if not acquired:
                try:
                    response_q.put({"error": "Inference queue full, request timed out after 2 minutes"})
                except (queue.Full, RuntimeError):
                    pass
                continue

            try:
                print(f"  [WORKER] Processing query: {query[:60]}...", flush=True)

                # Capture session once for this request to avoid race with /api/new_session
                # swapping the global between our multiple _get_active_session() calls.
                session = _get_active_session()

                # ── Identity Recognition ──
                # Recognize WHO is talking and inject relationship context
                identity_context = ""
                recognized_user = None
                if _identity_anchor:
                    try:
                        recognized_user = _identity_anchor.recognize(query)
                        if recognized_user:
                            identity_context = _identity_anchor.get_identity_context(recognized_user)
                            # NOTE: identity info is NEVER logged or returned in API responses
                            print(f"  [WORKER] Identity: recognized (context injected)", flush=True)
                    except Exception as e:
                        print(f"  [WORKER] Identity recognition skipped: {e}", flush=True)

                # ── Behavior Governor Pre-Evaluation ──
                # Determines memory budget, identity budget, response length
                governor_decision = None
                identity_confidence = 0.0
                if recognized_user and _identity_anchor and recognized_user in _identity_anchor.identities:
                    identity_confidence = _identity_anchor.identities[recognized_user].recognition_confidence
                substrate_pressure = 0.0
                try:
                    from inference.substrate_awareness import SubstrateMonitor
                    sm = SubstrateMonitor()
                    substrate_pressure = sm.get_pressure()
                except Exception:
                    pass

                if _behavior_governor:
                    try:
                        # Classify query for governor (lightweight)
                        from codette_forge_bridge import QueryClassifier, QueryComplexity
                        qc = QueryClassifier()
                        complexity = qc.classify(query)
                        classification = {
                            "complexity": complexity.name if hasattr(complexity, 'name') else str(complexity),
                            "domain": "general",
                        }
                        governor_decision = _behavior_governor.pre_evaluate(
                            query, classification,
                            identity_confidence=identity_confidence,
                            substrate_pressure=substrate_pressure,
                        )
                        print(f"  [GOVERNOR] {governor_decision.reasoning}", flush=True)

                        # Apply governor's identity budget
                        if governor_decision.identity_budget == "none":
                            identity_context = ""  # Governor says no identity
                    except Exception as e:
                        print(f"  [GOVERNOR] Pre-eval skipped: {e}", flush=True)

                # ── Memory Enrichment ──
                # Recall relevant cocoons — budget controlled by governor
                memory_budget = 3
                if governor_decision:
                    memory_budget = governor_decision.memory_budget
                enriched_query = query
                memory_context_summary = {
                    "continuity_summary_used": False,
                    "session_markers_used": 0,
                    "decision_landmarks_used": 0,
                    "recalled_cocoons_used": 0,
                    "value_analyses_used": 0,
                    "web_research_used": 0,
                    "web_search_trigger": web_search_trigger,
                }
                web_sources = []
                allow_web_search = bool(request.get("allow_web_search"))

                # Recent session context first — keeps local continuity stable
                try:
                    if session:
                        continuity_summary = session.active_continuity_summary or session.refresh_active_continuity_summary()
                        if continuity_summary:
                            memory_context_summary["continuity_summary_used"] = True
                            enriched_query = (
                                query + "\n\n---\n"
                                "# ACTIVE CONTINUITY SUMMARY\n"
                                f"{continuity_summary}\n"
                                "---"
                            )
                            print("  [WORKER] Injected active continuity summary", flush=True)
                        session_context = session.build_prompt_context(
                            max_turns=max(2, min(memory_budget + 1, 5)),
                            max_chars=900,
                        )
                        if session_context:
                            marker_count = session_context.count("\n") + 1
                            memory_context_summary["session_markers_used"] = marker_count
                            enriched_query = (
                                enriched_query + "\n\n---\n"
                                "# CURRENT SESSION CONTEXT\n"
                                "Keep continuity with these recent turns:\n"
                                f"{session_context}\n"
                                "---"
                            )
                            print(f"  [WORKER] Injected {marker_count} session memory markers", flush=True)
                        landmarks = session.get_recent_decision_landmarks(max_items=3)
                        landmarks = [
                            item for item in landmarks
                            if not is_ephemeral_response_constraint_text(item.get("summary", ""))
                        ]
                        if landmarks:
                            landmark_lines = [
                                f"- {item.get('label', 'Decision')}: {item.get('summary', '')}"
                                for item in landmarks
                            ]
                            memory_context_summary["decision_landmarks_used"] = len(landmark_lines)
                            enriched_query = (
                                enriched_query + "\n\n---\n"
                                "# DECISION LANDMARKS\n"
                                "Honor these active decisions and constraints:\n"
                                f"{chr(10).join(landmark_lines)}\n"
                                "---"
                            )
                            print(f"  [WORKER] Injected {len(landmark_lines)} decision landmarks", flush=True)
                except Exception as e:
                    print(f"  [WORKER] Session context skipped: {e}", flush=True)

                try:
                    # Use UnifiedMemory (SQLite + FTS5) when available,
                    # fall back to CognitionCocooner (JSON scan)
                    relevant_cocoons = []
                    value_analysis_cocoons = []
                    decision_landmark_cocoons = []
                    web_research_cocoons = []
                    if _unified_memory:
                        relevant_cocoons = _unified_memory.recall_relevant(query, max_results=memory_budget)
                        value_analysis_cocoons = _unified_memory.recall_value_analyses(query, max_results=max(1, min(2, memory_budget)))
                        decision_landmark_cocoons = _unified_memory.recall_by_domain("decision_landmark", limit=max(1, min(2, memory_budget)))
                        if allow_web_search:
                            web_research_cocoons = _unified_memory.recall_web_research(query, max_results=2)
                        recall_source = "unified_memory"
                    else:
                        from reasoning_forge.cognition_cocooner import CognitionCocooner
                        cocooner = CognitionCocooner(storage_path="cocoons")
                        relevant_cocoons = cocooner.recall_relevant(query, max_results=memory_budget)
                        recall_source = "cocooner"

                    memory_lines = []
                    if relevant_cocoons:
                        for cocoon in relevant_cocoons:
                            q = cocoon.get("query", "")[:100]
                            r = cocoon.get("response", "")[:200]
                            if q and r:
                                memory_lines.append(f"- Q: {q}\n  A: {r}")
                            memory_context_summary["recalled_cocoons_used"] += 1

                    value_lines = []
                    if value_analysis_cocoons:
                        for cocoon in value_analysis_cocoons:
                            meta = cocoon.get("metadata", {})
                            analysis_type = meta.get("analysis_type", "event_embedded_value")
                            analysis = meta.get("analysis", {})
                            if analysis_type == "risk_frontier":
                                best = (analysis or {}).get("best_scenario", {}).get("name", "unknown")
                                worst = (analysis or {}).get("worst_scenario", {}).get("name", "unknown")
                                value_lines.append(f"- Frontier memory: best={best}, worst={worst}")
                            else:
                                value_lines.append(
                                    f"- Valuation memory: combined_total={analysis.get('combined_total')}, "
                                    f"singularity={analysis.get('singularity_detected')}"
                                )
                            memory_context_summary["value_analyses_used"] += 1

                    decision_lines = []
                    if decision_landmark_cocoons:
                        for cocoon in decision_landmark_cocoons:
                            meta = cocoon.get("metadata", {})
                            decision_text = cocoon.get("query", "")[:180]
                            if is_ephemeral_response_constraint_text(decision_text):
                                continue
                            decision_lines.append(
                                f"- {meta.get('label', 'Decision')}: {decision_text}"
                            )

                    web_lines = []
                    if web_research_cocoons:
                        for cocoon in web_research_cocoons:
                            sources = cocoon.get("metadata", {}).get("sources", [])
                            for source in sources[:3]:
                                web_sources.append(source)
                            summary = cocoon.get("response", "")[:280]
                            if summary:
                                web_lines.append(f"- Cached research: {summary}")
                            memory_context_summary["web_research_used"] += 1

                    if memory_lines or value_lines or decision_lines or web_lines:
                        sections = []
                        if memory_lines:
                            sections.append(
                                "# YOUR PAST REASONING (relevant memories)\n"
                                "You previously responded to similar questions:\n" +
                                "\n".join(memory_lines)
                            )
                        if value_lines:
                            sections.append(
                                "# PAST VALUE ANALYSES\n"
                                "Relevant singularity/frontier runs from memory:\n" +
                                "\n".join(value_lines)
                            )
                        if decision_lines:
                            sections.append(
                                "# PAST DECISION LANDMARKS\n"
                                "Previously established constraints and commitments:\n" +
                                "\n".join(decision_lines)
                            )
                        if web_lines:
                            sections.append(
                                "# PAST WEB RESEARCH\n"
                                "Previously researched current-information notes:\n" +
                                "\n".join(web_lines)
                            )
                        enriched_query = (
                            enriched_query + "\n\n---\n" +
                            "\n\n".join(sections) +
                            "\n---\n"
                            "Use these memories for continuity and consistency. Build on past insights when relevant."
                        )
                        print(
                            f"  [WORKER] Injected {memory_context_summary['recalled_cocoons_used']} memories and "
                            f"{memory_context_summary['value_analyses_used']} value analyses ({recall_source})",
                            flush=True
                        )
                except Exception as e:
                    print(f"  [WORKER] Memory recall skipped: {e}", flush=True)

                if allow_web_search:
                    try:
                        live_web_results = []
                        if memory_context_summary["web_research_used"] == 0:
                            from web_search import research_query
                            live_web_results = [item.to_dict() for item in research_query(query, max_results=3)]
                            if live_web_results and _unified_memory:
                                _unified_memory.store_web_research(
                                    query=query,
                                    summary=_summarize_web_research(live_web_results),
                                    sources=live_web_results,
                                )
                            web_sources.extend(live_web_results)
                            memory_context_summary["web_research_used"] += len(live_web_results)
                        if web_sources:
                            enriched_query = (
                                enriched_query + "\n\n---\n" +
                                _summarize_web_research(web_sources[:3]) +
                                "\n---\n"
                                "Use these cited web findings for current facts. Distinguish sourced facts from your own inference."
                            )
                            print(f"  [WORKER] Injected {len(web_sources[:3])} web research sources", flush=True)
                    except Exception as e:
                        print(f"  [WORKER] Web research skipped: {e}", flush=True)

                # ── Identity Context Injection ──
                # Append identity context AFTER memory context
                # This goes into the prompt so Codette knows WHO she's talking to
                # Privacy: identity_context is NEVER returned in API responses
                if identity_context:
                    enriched_query = (
                        enriched_query + "\n\n---\n" + identity_context + "\n---"
                    )

                if _forge_bridge:
                    print(f"  [WORKER] Using forge bridge (Phase 6/7)", flush=True)
                    gov_mem_budget = governor_decision.memory_budget if governor_decision else 3
                    gov_max_tokens = governor_decision.max_response_tokens if governor_decision else 512
                    result = _forge_bridge.generate(
                        enriched_query, adapter=adapter, max_adapters=max_adapters,
                        memory_budget=gov_mem_budget, max_response_tokens=gov_max_tokens,
                    )
                else:
                    print(f"  [WORKER] Using direct orchestrator", flush=True)
                    result = orch.route_and_generate(
                        enriched_query,
                        max_adapters=max_adapters,
                        strategy="keyword",
                        force_adapter=adapter if adapter and adapter != "auto" else None,
                    )
                print(f"  [WORKER] Got result: response={len(result.get('response',''))} chars, adapter={result.get('adapter','?')}", flush=True)

                # ── Post-generation Hallucination Check ──
                response_text = result.get("response", "")
                hallucination_alerts = []

                # Check for artist/discography hallucinations
                artist_patterns = [
                    (r'(passed away|died|deceased).*?(19|20)\d{2}', "unverified artist death claim"),
                    (r'(the album|released).*?["\'](\w+[\w\s]*?)["\'].*?(19|20)\d{2}', "unverified album/date claim"),
                ]
                for pattern, alert_type in artist_patterns:
                    if re.search(pattern, response_text, re.IGNORECASE):
                        for artist in ["laney wilson", "megan moroney", "tyler childers"]:
                            if artist in response_text.lower():
                                hallucination_alerts.append(f"[HALLUCINATION] {alert_type} for {artist}")
                                break

                # If hallucinations detected, add self-correction
                if hallucination_alerts and is_artist_query:
                    correction = (
                        "\n\n---\n"
                        "[Self-Correction]\n"
                        "I just realized I made some unverified claims above. Rather than guess, "
                        "I should be honest: I don't have reliable biographical details about this artist. "
                        "For accurate information, check Wikipedia, Spotify, or their official website. "
                        "I'm better at helping with production techniques, music theory, and sound design.\n"
                    )
                    result["response"] = response_text + correction
                    result["hallucination_detected"] = True
                    result["hallucination_alerts"] = hallucination_alerts
                    for alert in hallucination_alerts:
                        print(f"  {alert}", flush=True)
                else:
                    result["hallucination_detected"] = False

                adapter_for_analysis = result.get("adapter", "base")
                if isinstance(adapter_for_analysis, list):
                    adapter_for_analysis = adapter_for_analysis[0] if adapter_for_analysis else "base"
                reliability = _analyze_response_reliability(
                    result.get("response", ""),
                    adapter_for_analysis,
                    domain=result.get("domain", "general"),
                )
                result["response_confidence"] = reliability["response_confidence"]
                result["confidence_analysis"] = reliability
                if reliability["hallucination_detected"]:
                    existing_alerts = list(result.get("hallucination_alerts", []))
                    result["hallucination_detected"] = True
                    result["hallucination_alerts"] = existing_alerts + reliability["hallucination_signals"]
                if (
                    reliability["response_confidence"] < 0.45
                    and result.get("response", "").strip()
                    and "Confidence note:" not in result.get("response", "")
                ):
                    result["response"] = (
                        result["response"].rstrip() +
                        "\n\nConfidence note: parts of this answer may be uncertain. "
                        "Treat factual specifics carefully and verify important claims."
                    )

                if _behavior_governor and governor_decision:
                    validation = {}
                    try:
                        validation = _behavior_governor.post_validate(
                            query, result.get("response", ""), governor_decision
                        )
                        if validation.get("warnings"):
                            for w in validation["warnings"]:
                                print(f"  [GOVERNOR] {w}", flush=True)
                        if "identity_leak" in validation.get("corrections", []):
                            print(f"  [GOVERNOR] Identity leak detected in response", flush=True)
                    except Exception:
                        pass
                else:
                    validation = {}

                # Update session with response data (drives cocoon metrics UI)
                epistemic = None
                if session:
                    try:
                        # Add user message + assistant response to session history
                        session.add_message("user", query)
                        session.add_message("assistant", result.get("response", ""), metadata={
                            "adapter": result.get("adapter", "base"),
                            "tokens": result.get("tokens", 0),
                        })

                        # Update cocoon state (spiderweb, coherence, attractors, glyphs, etc.)
                        adapter_name = result.get("adapter", "base")
                        if isinstance(adapter_name, list):
                            adapter_name = adapter_name[0] if adapter_name else "base"
                        route_obj = result.get("route")
                        perspectives_dict = result.get("perspectives")
                        session.update_after_response(
                            route_obj, adapter_name, perspectives=perspectives_dict
                        )

                        # Get epistemic report from session metrics
                        if session.coherence_history or session.tension_history:
                            epistemic = {
                                "ensemble_coherence": session.coherence_history[-1] if session.coherence_history else 0,
                                "tension_magnitude": session.tension_history[-1] if session.tension_history else 0,
                            }
                            # Add ethical alignment from AEGIS if available
                            if hasattr(session, 'aegis') and session.aegis:
                                try:
                                    aegis_state = session.aegis.get_state() if hasattr(session.aegis, 'get_state') else {}
                                    if aegis_state.get('eta') is not None:
                                        epistemic["ethical_alignment"] = aegis_state['eta']
                                except Exception:
                                    pass
                    except Exception as e:
                        print(f"  [WORKER] Session update failed (non-critical): {e}", flush=True)

                # ── Store in Unified Memory ──
                # Every response goes to SQLite for future FTS5 recall
                if _unified_memory:
                    try:
                        if session:
                            for landmark in session.get_recent_decision_landmarks(max_items=3):
                                if landmark.get("persisted"):
                                    continue
                                summary = landmark.get("summary", "")
                                if not summary:
                                    continue
                                cocoon_id = _unified_memory.store(
                                    query=summary,
                                    response=summary,
                                    adapter="decision_landmark",
                                    domain="decision_landmark",
                                    complexity="SESSION",
                                    importance=9,
                                    metadata={
                                        "memory_type": "decision_landmark",
                                        "success": True,
                                        "label": landmark.get("label", "Decision"),
                                        "role": landmark.get("role", "assistant"),
                                        "session_id": session.session_id,
                                        "continuity_summary": session.active_continuity_summary,
                                    },
                                )
                                session.mark_decision_landmark_persisted(summary, cocoon_id)

                        adapter_for_store = result.get("adapter", "base")
                        if isinstance(adapter_for_store, list):
                            adapter_for_store = adapter_for_store[0] if adapter_for_store else "base"
                        route_confidence = route.get("confidence", 0) if isinstance(route, dict) else (route.confidence if route else 0)
                        route_snapshot = {
                            "primary": route.get("primary") if isinstance(route, dict) else (route.primary if route else adapter_for_store),
                            "secondary": route.get("secondary", []) if isinstance(route, dict) else (route.secondary if route else []),
                            "confidence": route_confidence,
                            "reasoning": route.get("reasoning", "") if isinstance(route, dict) else (route.reasoning if route else ""),
                            "strategy": route.get("strategy", "") if isinstance(route, dict) else (route.strategy if route else ""),
                            "multi_perspective": route.get("multi_perspective", False) if isinstance(route, dict) else (route.multi_perspective if route else False),
                        }
                        response_success = bool(result.get("response", "").strip()) and not result.get("hallucination_detected", False)
                        if validation.get("warnings"):
                            response_success = False
                        cocoon_id = _unified_memory.store(
                            query=query,
                            response=result.get("response", ""),
                            adapter=adapter_for_store,
                            domain=result.get("domain", "general"),
                            complexity=result.get("complexity", "MEDIUM"),
                            metadata={
                                "success": response_success,
                                "coherence": (epistemic or {}).get("ensemble_coherence"),
                                "epistemic": epistemic or {},
                                "route": route_snapshot,
                                "memory_context": memory_context_summary,
                                "trust_tags": _build_trust_tags(result, memory_context_summary),
                                "web_sources": web_sources[:5],
                                "hallucination_detected": result.get("hallucination_detected", False),
                                "response_confidence": result.get("response_confidence", 0.5),
                                "confidence_analysis": result.get("confidence_analysis", {}),
                                "governor": {
                                    "memory_budget": governor_decision.memory_budget if governor_decision else None,
                                    "max_response_tokens": governor_decision.max_response_tokens if governor_decision else None,
                                    "warnings": validation.get("warnings", []),
                                },
                                "tools_used": result.get("tools_used", []),
                            },
                        )
                        memory_weighting = _get_memory_weighting()
                        if memory_weighting:
                            memory_weighting.compute_weights(force_recompute=True)
                        if _behavior_governor and governor_decision:
                            _behavior_governor.record_outcome(
                                domain=result.get("domain", "general"),
                                complexity=str(result.get("complexity", "MEDIUM")),
                                success=response_success,
                                actual_tokens=int(result.get("tokens", 0) or 0),
                                memory_budget_used=int(memory_budget or 0),
                            )
                    except Exception:
                        pass

                # ── Identity Update (post-interaction) ──
                # Update relationship state — trust grows, topics tracked
                # Privacy: only internal state updated, nothing exposed
                if _identity_anchor and recognized_user:
                    try:
                        adapter_name_for_id = result.get("adapter", "base")
                        if isinstance(adapter_name_for_id, list):
                            adapter_name_for_id = adapter_name_for_id[0] if adapter_name_for_id else "base"
                        _identity_anchor.update_after_interaction(
                            user_id=recognized_user,
                            query=query,
                            response=result.get("response", ""),
                            adapter=adapter_name_for_id,
                        )
                    except Exception:
                        pass  # Non-critical, never fail on identity

                # Extract route info from result (if available from ForgeEngine)
                route = result.get("route")
                perspectives = result.get("perspectives", [])

                # Build response
                response_text = result.get("response", "")
                if not response_text:
                    print(f"  [WORKER] WARNING: Empty response! Full result keys: {list(result.keys())}", flush=True)
                    print(f"  [WORKER] Result dump: { {k: str(v)[:100] for k,v in result.items()} }", flush=True)
                response_data = {
                    "event": "complete",
                    "response": response_text or "[No response generated — check server logs]",
                    "adapter": result.get("adapter",
                        result.get("adapters", ["base"])[0] if isinstance(result.get("adapters"), list) else "base"),
                    "confidence": route.get("confidence", 0) if isinstance(route, dict) else (route.confidence if route else 0),
                    "reasoning": route.get("reasoning", "") if isinstance(route, dict) else (route.reasoning if route else ""),
                    "tokens": result.get("tokens", 0),
                    "time": round(result.get("time", 0), 2),
                    "multi_perspective": route.get("multi_perspective", False) if isinstance(route, dict) else (route.multi_perspective if route else False),
                    "response_confidence": result.get("response_confidence", 0.5),
                    "confidence_analysis": result.get("confidence_analysis", {}),
                    "trust_tags": _build_trust_tags(result, memory_context_summary),
                    "web_sources": web_sources[:5],
                    "web_used": bool(web_sources),
                    "web_search_trigger": web_search_trigger,
                }
                response_data["memory_context"] = memory_context_summary

                # Add Phase 6 metadata (complexity, domain, ethical)
                if result.get("complexity"):
                    response_data["complexity"] = str(result["complexity"])
                if result.get("domain"):
                    response_data["domain"] = result["domain"]

                # Add ethical governance info
                ethical_checks = 0
                if _forge_bridge and hasattr(_forge_bridge, 'forge'):
                    fg = _forge_bridge.forge
                    if hasattr(fg, 'ethical_governance') and fg.ethical_governance:
                        ethical_checks = len(getattr(fg.ethical_governance, 'audit_log', []))
                        response_data["ethical_checks"] = ethical_checks

                # Add updated memory count from cocoon
                if _forge_bridge and hasattr(_forge_bridge, 'forge') and hasattr(_forge_bridge.forge, 'memory_kernel') and _forge_bridge.forge.memory_kernel:
                    response_data["memory_count"] = len(_forge_bridge.forge.memory_kernel.memories)

                # Add perspectives if available
                if perspectives:
                    response_data["perspectives"] = perspectives

                # Cocoon state — send full session state for UI metrics panel
                if session:
                    try:
                        session_state = session.get_state()
                        response_data["cocoon"] = session_state
                    except Exception as e:
                        print(f"  [WORKER] Session state serialization failed: {e}", flush=True)

                # Add epistemic report if available
                if epistemic:
                    response_data["epistemic"] = epistemic

                # Add tool usage info if any tools were called
                tools_used = result.get("tools_used", [])
                if tools_used:
                    response_data["tools_used"] = tools_used

                # RE-CHECK response queue still exists (handler may have cleaned it up if timeout fired)
                with _response_queues_lock:
                    response_q_still_exists = req_id in _response_queues

                if response_q_still_exists:
                    try:
                        response_q.put(response_data)
                    except (queue.Full, RuntimeError) as e:
                        print(f"  ERROR: Failed to queue response: {e}")
                else:
                    print(f"  WARNING: Response queue was cleaned up (handler timeout) - response dropped for {req_id}")

            except Exception as e:
                print(f"  ERROR during inference: {e}")
                traceback.print_exc()

                # DEFENSIVE: RE-CHECK response queue before putting error
                with _response_queues_lock:
                    response_q_still_exists = req_id in _response_queues

                if response_q_still_exists:
                    try:
                        response_q.put({"event": "error", "error": str(e)})
                    except (queue.Full, RuntimeError):
                        print(f"  ERROR: Also failed to queue error response")
                else:
                    print(f"  WARNING: Response queue was cleaned up (handler timeout) - error response dropped for {req_id}")
            finally:
                # Always release the semaphore
                _inference_semaphore.release()

        except Exception as e:
            print(f"  ERROR in worker thread: {e}")
            traceback.print_exc()


class CodetteHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for Codette API + static files."""

    # Serve static files from inference/static/
    def __init__(self, *args, **kwargs):
        static_dir = str(Path(__file__).parent / "static")
        super().__init__(*args, directory=static_dir, **kwargs)

    def log_message(self, format, *args):
        """Quieter logging — skip static file requests."""
        msg = format % args
        if not any(ext in msg for ext in [".css", ".js", ".ico", ".png", ".woff"]):
            print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path == "/api/status":
            # Dynamically update memory count from forge kernel
            if _forge_bridge and hasattr(_forge_bridge, 'forge') and hasattr(_forge_bridge.forge, 'memory_kernel') and _forge_bridge.forge.memory_kernel:
                with _orchestrator_status_lock:
                    _orchestrator_status["memory_count"] = len(_forge_bridge.forge.memory_kernel.memories)
            self._json_response(_orchestrator_status)
        elif path == "/api/session":
            self._json_response(_session.get_state() if _session else {})
        elif path == "/api/sessions":
            sessions = _session_store.list_sessions() if _session_store else []
            self._json_response({"sessions": sessions})
        elif path == "/api/adapters":
            self._json_response({
                "colors": ADAPTER_COLORS,
                "agents": AGENT_NAMES,
                "available": _orchestrator.available_adapters if _orchestrator else [],
            })
        elif path == "/api/health":
            try:
                self._json_response(_run_health_check())
            except Exception as e:
                self._json_response({"overall": "ERROR", "detail": str(e)})
        elif path == "/api/introspection":
            try:
                # Use unified memory if available, fall back to legacy
                if _unified_memory:
                    self._json_response(_unified_memory.full_introspection())
                else:
                    from cocoon_introspection import CocoonIntrospectionEngine
                    engine = CocoonIntrospectionEngine()
                    self._json_response(engine.full_introspection())
            except Exception as e:
                self._json_response({"error": str(e)})
        elif path == "/api/governor":
            # Confidence dashboard — governor state, identity confidence, memory stats
            # NOTE: identity details are NEVER exposed (privacy)
            dashboard = {"governor": None, "memory": None, "identity_summary": None}
            if _behavior_governor:
                dashboard["governor"] = _behavior_governor.get_state()
            if _unified_memory:
                dashboard["memory"] = _unified_memory.get_stats()
            if _identity_anchor:
                # Safe summary: only counts and trust levels, no PII
                dashboard["identity_summary"] = {
                    "known_identities": len(_identity_anchor.identities),
                    "current_user_recognized": _identity_anchor.current_user is not None,
                    # Confidence level only (not who)
                    "current_confidence": (
                        _identity_anchor.identities[_identity_anchor.current_user].recognition_confidence
                        if _identity_anchor.current_user and _identity_anchor.current_user in _identity_anchor.identities
                        else 0.0
                    ),
                }
            self._json_response(dashboard)
        elif path == "/api/synthesize":
            # Meta-cognitive cocoon synthesis — discover patterns, forge strategies
            try:
                params = parse_qs(parsed.query)
                problem = params.get("problem", ["How should an AI decide when to change its own thinking patterns?"])[0]
                valuation_payload = None
                if "valuation_payload" in params:
                    try:
                        valuation_payload = json.loads(params["valuation_payload"][0])
                    except Exception:
                        valuation_payload = None
                if _forge_bridge and hasattr(_forge_bridge, 'forge') and hasattr(_forge_bridge.forge, 'cocoon_synthesizer') and _forge_bridge.forge.cocoon_synthesizer:
                    result = _forge_bridge.forge.synthesize_from_cocoons(problem, valuation_payload=valuation_payload)
                    self._json_response(result)
                elif _unified_memory:
                    from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                    from reasoning_forge.event_embedded_value import EventEmbeddedValueEngine
                    synth = CocoonSynthesizer(memory=_unified_memory)
                    valuation_analysis = (
                        EventEmbeddedValueEngine().analyze_payload(valuation_payload)
                        if valuation_payload else None
                    )
                    comparison = synth.run_full_synthesis(problem, valuation_analysis=valuation_analysis)
                    self._json_response({
                        "readable": comparison.to_readable(),
                        "structured": comparison.to_dict(),
                    })
                else:
                    # Standalone mode — use filesystem cocoons
                    from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                    from reasoning_forge.event_embedded_value import EventEmbeddedValueEngine
                    synth = CocoonSynthesizer()
                    valuation_analysis = (
                        EventEmbeddedValueEngine().analyze_payload(valuation_payload)
                        if valuation_payload else None
                    )
                    comparison = synth.run_full_synthesis(problem, valuation_analysis=valuation_analysis)
                    self._json_response({
                        "readable": comparison.to_readable(),
                        "structured": comparison.to_dict(),
                    })
            except Exception as e:
                import traceback
                self._json_response({"error": str(e), "traceback": traceback.format_exc()})
        elif path == "/api/value-analysis":
            try:
                params = parse_qs(parsed.query)
                payload = {
                    "intervals": [],
                    "events": [],
                    "singularity_mode": params.get("singularity_mode", ["strict"])[0],
                }
                if _forge_bridge and hasattr(_forge_bridge, "forge") and hasattr(_forge_bridge.forge, "analyze_event_embedded_value"):
                    self._json_response(_forge_bridge.forge.analyze_event_embedded_value(payload))
                else:
                    from reasoning_forge.event_embedded_value import EventEmbeddedValueEngine
                    self._json_response(EventEmbeddedValueEngine().analyze_payload(payload))
            except Exception as e:
                import traceback
                self._json_response({"error": str(e), "traceback": traceback.format_exc()})
        elif path == "/api/search":
            q = parse_qs(parsed.query).get("q", [""])[0].strip()
            if not q:
                self._json_response({"error": "q parameter required", "results": []})
            else:
                results = []
                try:
                    # FTS5 search via UnifiedMemory
                    if _unified_memory and hasattr(_unified_memory, 'search'):
                        for cocoon in _unified_memory.search(q, limit=10):
                            results.append({
                                "source": "unified",
                                "title": getattr(cocoon, 'title', ''),
                                "content": getattr(cocoon, 'content', '')[:200],
                                "domain": getattr(cocoon, 'domain', ''),
                                "timestamp": getattr(cocoon, 'timestamp', 0),
                            })
                    # Fallback: kernel full-text search
                    if not results:
                        kernel = None
                        if _forge_bridge and hasattr(_forge_bridge, 'forge'):
                            kernel = getattr(_forge_bridge.forge, 'memory_kernel', None)
                        if kernel and hasattr(kernel, 'search'):
                            for m in kernel.search(q, limit=10):
                                results.append({
                                    "source": "kernel",
                                    "title": getattr(m, 'title', ''),
                                    "content": getattr(m, 'content', '')[:200],
                                    "domain": getattr(m, 'adapter_used', ''),
                                    "timestamp": getattr(m, 'timestamp', 0),
                                })
                except Exception as e:
                    results = [{"error": str(e)}]
                self._json_response({"query": q, "results": results})
        elif path == "/api/drift":
            self._json_response(self._build_drift_payload())
        elif path == "/api/chat":
            # SSE endpoint for streaming
            self._handle_chat_sse(parsed)
        elif path == "/":
            # Serve index.html
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def end_headers(self):
        """Add no-cache headers for static files during development."""
        if self.path and any(self.path.endswith(ext) for ext in ('.html', '.js', '.css')):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            self._handle_chat_post()
        elif path == "/api/session/new":
            self._handle_new_session()
        elif path == "/api/session/load":
            self._handle_load_session()
        elif path == "/api/session/save":
            self._handle_save_session()
        elif path == "/api/session/export":
            self._handle_export_session()
        elif path == "/api/session/import":
            self._handle_import_session()
        elif path == "/api/resolve_hook":
            try:
                data = self._read_json_body()
                hook_text = data.get("hook", "").strip()
                if not hook_text:
                    self._json_response({"error": "hook field required"}, status=400)
                    return
                kernel = None
                if _forge_bridge and hasattr(_forge_bridge, 'forge'):
                    kernel = getattr(_forge_bridge.forge, 'memory_kernel', None)
                if kernel is None:
                    self._json_response({"error": "memory_kernel not available"})
                    return
                resolved = kernel.resolve_hook(hook_text)
                self._json_response({"resolved": resolved, "hook": hook_text})
            except Exception as e:
                self._json_response({"error": str(e)})
        elif path == "/api/synthesize":
            # POST handler for cocoon synthesis with custom problem
            try:
                data = self._read_json_body()
                problem = data.get("problem", "How should an AI decide when to change its own thinking patterns?")
                domains = data.get("domains", None)
                valuation_payload = data.get("valuation_payload")
                if _forge_bridge and hasattr(_forge_bridge, "forge") and hasattr(_forge_bridge.forge, "synthesize_from_cocoons"):
                    self._json_response(
                        _forge_bridge.forge.synthesize_from_cocoons(
                            problem,
                            domains=domains,
                            valuation_payload=valuation_payload,
                        )
                    )
                else:
                    from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                    from reasoning_forge.event_embedded_value import EventEmbeddedValueEngine
                    if _unified_memory:
                        synth = CocoonSynthesizer(memory=_unified_memory)
                    else:
                        synth = CocoonSynthesizer()
                    valuation_analysis = (
                        EventEmbeddedValueEngine().analyze_payload(valuation_payload)
                        if valuation_payload else None
                    )
                    comparison = synth.run_full_synthesis(problem, domains, valuation_analysis=valuation_analysis)
                    self._json_response({
                        "readable": comparison.to_readable(),
                        "structured": comparison.to_dict(),
                    })
            except Exception as e:
                import traceback
                self._json_response({"error": str(e), "traceback": traceback.format_exc()})
        elif path == "/api/value-analysis":
            try:
                data = self._read_json_body()
                if _forge_bridge and hasattr(_forge_bridge, "forge") and hasattr(_forge_bridge.forge, "analyze_event_embedded_value"):
                    result = _forge_bridge.forge.analyze_event_embedded_value(data)
                else:
                    from reasoning_forge.event_embedded_value import EventEmbeddedValueEngine
                    result = EventEmbeddedValueEngine().analyze_payload(data)
                self._json_response(result)
            except Exception as e:
                import traceback
                self._json_response({"error": str(e), "traceback": traceback.format_exc()})
        else:
            self.send_error(404, "Not found")

    def _build_drift_payload(self) -> dict:
        """Collect live resonance state from the forge engine for the drift panel."""
        payload = {
            "psi_r": 0.0,
            "psi_history": [],
            "epsilon": 0.0,
            "gamma": 0.0,
            "hooks": [],
            "state": "idle",
        }

        forge = None
        if _forge_bridge and hasattr(_forge_bridge, 'forge'):
            forge = _forge_bridge.forge

        if forge is None:
            return payload

        # psi_r + psi_history from ResonantContinuityEngine
        re = getattr(forge, 'resonance_engine', None)
        if re and getattr(re, 'history', None):
            history = re.history
            current = history[-1]
            payload["psi_r"] = round(float(current.psi_r), 4)
            payload["psi_history"] = [
                round(float(s.psi_r), 4) for s in history[-64:]
            ]
            payload["epsilon"] = round(float(current.darkness), 4)
            payload["gamma"] = round(float(current.coherence), 4)

        # Fallback gamma from spiderweb phase coherence
        if payload["gamma"] == 0.0:
            sw = getattr(forge, 'spiderweb', None)
            if sw and hasattr(sw, 'phase_coherence'):
                try:
                    payload["gamma"] = round(float(sw.phase_coherence()), 4)
                except Exception:
                    pass

        # Hooks: from memory kernel's open follow-up hooks
        kernel = getattr(forge, 'memory_kernel', None)
        if kernel:
            try:
                hooked = kernel.recall_with_hooks(limit=12)
                seen: set = set()
                for m in hooked:
                    for h in getattr(m, 'follow_up_hooks', []):
                        if h not in seen:
                            seen.add(h)
                            payload["hooks"].append({
                                "label": h,
                                "strength": round(float(getattr(m, 'importance', 5)) / 10.0, 2),
                            })
                            if len(payload["hooks"]) >= 12:
                                break
                    if len(payload["hooks"]) >= 12:
                        break
            except Exception:
                pass

        # Derive state label
        e = payload["epsilon"]
        g = payload["gamma"]
        if e < 0.25 and g > 0.75:
            payload["state"] = "coherent"
        elif e > 0.65:
            payload["state"] = "high-tension"
        elif g > 0.5:
            payload["state"] = "resonant"
        elif payload["psi_r"] != 0.0:
            payload["state"] = "drifting"

        return payload

    def _json_response(self, data, status=200):
        """Send a JSON response."""
        try:
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (ConnectionAbortedError, BrokenPipeError):
            # Client disconnected before response was fully sent — this is normal
            pass
        except Exception as e:
            print(f"  ERROR in _json_response: {e}")

    def _read_json_body(self):
        """Read and parse JSON POST body."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        return json.loads(body) if body else {}

    def _parse_multipart_chat(self):
        """Parse multipart/form-data for chat with file attachments."""
        try:
            content_type = self.headers.get("Content-Type", "")
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            environ = {
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': content_type,
                'CONTENT_LENGTH': str(length),
            }
            form = _FieldStorage(
                fp=BytesIO(body),
                headers=self.headers,
                environ=environ,
            )
        except Exception as e:
            print(f"  [WARN] Multipart parse failed: {e}, falling back to empty")
            return {"query": "", "adapter": None, "max_adapters": 2, "allow_web_search": False,
                    "file_count": 0, "file_errors": [str(e)], "has_file_context": False}

        # Extract text fields — getfirst returns str or None
        raw_query = form.getfirst("query", "")
        query = raw_query.strip() if isinstance(raw_query, str) else raw_query.decode('utf-8', errors='replace').strip()
        raw_adapter = form.getfirst("adapter", None)
        adapter = raw_adapter if raw_adapter else None
        raw_allow_web = form.getfirst("allow_web_search", "0")
        allow_web_search = str(raw_allow_web).lower() in {"1", "true", "yes", "on"}
        try:
            max_adapters = int(form.getfirst("max_adapters", "2"))
        except (ValueError, TypeError):
            max_adapters = 2

        # Process file attachments
        file_contexts = []
        file_errors = []
        guardian = _session.guardian if _session else None

        # Extract file items from the form — cgi.FieldStorage stores them
        # as FieldStorage objects with .filename set; non-file fields are
        # MiniFieldStorage (or plain bytes) without .filename
        file_items = []
        if "files" in form:
            raw = form["files"]
            # Could be a single item or a list
            if isinstance(raw, list):
                file_items = raw
            else:
                file_items = [raw]

        # Filter to actual file uploads (have .filename attribute and it's set)
        file_items = [f for f in file_items if hasattr(f, 'filename') and f.filename]

        if len(file_items) > 5:
            file_errors.append("Too many files (max 5)")
            file_items = file_items[:5]

        for item in file_items:
            file_data = item.file.read()
            if guardian:
                check = guardian.check_file_upload(item.filename, file_data)
            else:
                from reasoning_forge.guardian import CodetteGuardian
                check = CodetteGuardian().check_file_upload(item.filename, file_data)

            if check["safe"]:
                size_str = f"{len(file_data) / 1024:.1f} KB"
                file_contexts.append(
                    f"--- Attached File: {check['filename']} ({size_str}) ---\n"
                    f"{check['content']}\n"
                    f"--- End of File ---"
                )
            else:
                file_errors.append(f"{item.filename}: {check['error']}")

        # Prepend file content to query
        if file_contexts:
            file_block = "\n\n".join(file_contexts)
            query = f"{file_block}\n\n{query}"

        return {
            "query": query,
            "adapter": adapter,
            "max_adapters": max_adapters,
            "allow_web_search": allow_web_search,
            "file_count": len(file_contexts),
            "file_errors": file_errors,
            "has_file_context": len(file_contexts) > 0,
        }

    def _handle_chat_post(self):
        """Handle chat request — queue inference, return via SSE or JSON."""
        content_type = self.headers.get("Content-Type", "")

        if content_type.startswith("multipart/form-data"):
            data = self._parse_multipart_chat()
            has_file_context = data.get("has_file_context", False)
        else:
            data = self._read_json_body()
            has_file_context = False

        query = data.get("query", "").strip()
        adapter = data.get("adapter")
        max_adapters = data.get("max_adapters", 2)
        allow_web_search = bool(data.get("allow_web_search"))

        if not query:
            self._json_response({"error": "Empty query"}, 400)
            return

        # Return file errors as warnings (still process the query)
        file_errors = data.get("file_errors", [])

        # Guardian input check
        if _session and _session.guardian:
            check = _session.guardian.check_input(query, has_file_context=has_file_context)
            if not check["safe"]:
                query = check["cleaned_text"]

        allow_web_search, web_search_trigger = _resolve_web_research_request(query, allow_web_search)

        # Check if orchestrator is loading
        with _orchestrator_status_lock:
            status_state = _orchestrator_status.get("state")
        if status_state == "loading":
            self._json_response({
                "error": "Model is still loading, please wait...",
                "status": _orchestrator_status,
            }, 503)
            return

        # Queue the request
        req_id, response_q = _register_response_queue()

        _request_queue.put({
            "id": req_id,
            "query": query,
            "adapter": adapter,
            "max_adapters": max_adapters,
            "allow_web_search": allow_web_search,
            "web_search_trigger": web_search_trigger,
        })

        # Wait for response (with timeout)
        try:
            # First wait for thinking event (generous timeout for CPU inference)
            thinking = response_q.get(timeout=600)
            if "error" in thinking and thinking.get("event") != "thinking":
                self._json_response(thinking, 500)
                return

            # Wait for complete event (multi-perspective can take 15+ min on CPU)
            result = response_q.get(timeout=1200)  # 20 min max for inference
            # Attach file warnings if any
            if file_errors:
                result["file_warnings"] = file_errors
            if data.get("file_count"):
                result["files_attached"] = data["file_count"]
            self._json_response(result)

        except queue.Empty:
            self._json_response({"error": "Request timed out"}, 504)
        finally:
            _unregister_response_queue(req_id)

    def _handle_chat_sse(self, parsed):
        """Handle SSE streaming endpoint."""
        params = parse_qs(parsed.query)
        query = params.get("q", [""])[0]
        adapter = params.get("adapter", [None])[0]

        if not query:
            self.send_error(400, "Missing query parameter 'q'")
            return

        # Set up SSE headers
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        # Queue request
        req_id, response_q = _register_response_queue(prefix="sse")

        _request_queue.put({
            "id": req_id,
            "query": query,
            "adapter": adapter,
            "max_adapters": 2,
        })

        try:
            # Stream events
            while True:
                try:
                    event = response_q.get(timeout=300)
                except queue.Empty:
                    self._send_sse("error", {"error": "Timeout"})
                    break

                event_type = event.get("event", "message")
                self._send_sse(event_type, event)

                if event_type in ("complete", "error"):
                    break
        finally:
            _unregister_response_queue(req_id)

    def _send_sse(self, event_type, data):
        """Send a Server-Sent Event."""
        try:
            payload = f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass

    def _handle_new_session(self):
        """Create a new session."""
        session = _get_active_session()
        # Save current session first
        if session and _session_store and session.messages:
            try:
                _session_store.save(session)
            except Exception:
                pass

        session = CodetteSession()
        _set_active_session(session)
        # Reset sycophancy agreement-loop counter at each session boundary
        if _forge_bridge and hasattr(_forge_bridge, 'forge'):
            _sg = getattr(_forge_bridge.forge, '_sycophancy_guard', None)
            if _sg:
                _sg.reset_session()
        self._json_response({"session_id": session.session_id})

    def _handle_load_session(self):
        """Load a previous session."""
        data = self._read_json_body()
        session_id = data.get("session_id")

        if not session_id or not _session_store:
            self._json_response({"error": "Invalid session ID"}, 400)
            return

        loaded = _session_store.load(session_id)
        if loaded:
            _set_active_session(loaded)
            self._json_response({
                "session_id": loaded.session_id,
                "messages": loaded.messages,
                "state": loaded.get_state(),
            })
        else:
            self._json_response({"error": "Session not found"}, 404)

    def _handle_save_session(self):
        """Manually save current session."""
        session = _get_active_session()
        if session and _session_store:
            _session_store.save(session)
            self._json_response({"saved": True, "session_id": session.session_id})
        else:
            self._json_response({"error": "No active session"}, 400)

    def _handle_export_session(self):
        """Export current session as downloadable JSON."""
        session = _get_active_session()
        if not session:
            self._json_response({"error": "No active session"}, 400)
            return

        export_data = session.to_dict()
        export_data["_export_version"] = 1
        export_data["_exported_at"] = time.time()

        body = json.dumps(export_data, default=str, indent=2).encode("utf-8")
        filename = f"codette_session_{session.session_id[:8]}.json"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_import_session(self):
        """Import a session from uploaded JSON."""
        try:
            data = self._read_json_body()
            if not data or "session_id" not in data:
                self._json_response({"error": "Invalid session data"}, 400)
                return

            # Save current session before importing
            session = _get_active_session()
            if session and _session_store and session.messages:
                try:
                    _session_store.save(session)
                except Exception:
                    pass

            imported = CodetteSession()
            imported.from_dict(data)
            _set_active_session(imported)

            # Save imported session to store
            if _session_store:
                try:
                    _session_store.save(imported)
                except Exception:
                    pass

            self._json_response({
                "session_id": imported.session_id,
                "messages": imported.messages,
                "state": imported.get_state(),
                "imported": True,
            })
        except Exception as e:
            self._json_response({"error": f"Import failed: {e}"}, 400)


def main():
    global _session, _session_store, _worker_threads

    parser = argparse.ArgumentParser(description="Codette Web UI")
    parser.add_argument("--port", type=int, default=7860, help="Port (default: 7860)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    print("=" * 60)
    print("  CODETTE WEB UI")
    print("=" * 60)

    # Initialize session
    _session_store = SessionStore()
    _session = CodetteSession()
    print(f"  Session: {_session.session_id}")
    print(f"  Cocoon: spiderweb={_session.spiderweb is not None}, "
          f"metrics={_session.metrics_engine is not None}")

    # Start worker thread for request processing
    # NOTE: Only 1 worker needed — llama.cpp cannot parallelize inference.
    # With 1 semaphore + 1 worker, we avoid idle threads and deadlock risk.
    # Multiple workers would just spin waiting for the semaphore.
    num_workers = 1
    with _worker_threads_lock:
        for i in range(num_workers):
            worker = threading.Thread(target=_worker_thread, daemon=True, name=f"worker-{i}")
            worker.start()
            _worker_threads.append(worker)
    print(f"  Started {num_workers} worker thread for serial inference")

    # Start cleanup thread for orphaned response queues
    cleanup_thread = threading.Thread(target=_cleanup_orphaned_queues, daemon=True, name="cleanup")
    cleanup_thread.start()
    print(f"  Started cleanup thread for queue maintenance")

    # Start worker health monitor thread
    health_monitor = threading.Thread(target=_monitor_worker_health, daemon=True, name="health-monitor")
    health_monitor.start()
    print(f"  Started worker health monitor thread")

    # Start server FIRST so browser can connect immediately
    server = ThreadingHTTPServer(("127.0.0.1", args.port), CodetteHandler)
    url = f"http://localhost:{args.port}"
    print(f"\n  Server: {url}")
    print(f"  Press Ctrl+C to stop\n")

    # Open browser
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    # Start model loading in background (browser will show "loading" status)
    threading.Thread(target=_get_orchestrator, daemon=True).start()
    print(f"  Model loading in background (takes ~60s on first startup)...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        # Save session
        session = _get_active_session()
        if session and _session_store and session.messages:
            _session_store.save(session)
            print(f"  Session saved: {session.session_id}")
        _request_queue.put(None)  # Shutdown worker
        server.shutdown()
        print("  Goodbye!")


if __name__ == "__main__":
    main()
