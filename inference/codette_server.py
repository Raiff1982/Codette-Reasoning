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

import os, sys, json, time, threading, queue, argparse, webbrowser, traceback, re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from io import BytesIO

# Auto-configure environment
_site = r"J:\Lib\site-packages"
if _site not in sys.path:
    sys.path.insert(0, _site)
os.environ["PATH"] = r"J:\Lib\site-packages\Library\bin" + os.pathsep + os.environ.get("PATH", "")
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    # Force unbuffered output so cmd window updates in real-time
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Project imports
_inference_dir = str(Path(__file__).parent)
if _inference_dir not in sys.path:
    sys.path.insert(0, _inference_dir)

from codette_session import (
    CodetteSession, SessionStore, ADAPTER_COLORS, AGENT_NAMES
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

# Request queue for thread-safe model access
_request_queue = queue.Queue()
_response_queues = {}  # request_id -> queue.Queue
_response_queues_lock = threading.Lock()  # Protect _response_queues from race conditions
_queue_creation_times = {}  # Track when each queue was created for cleanup

# Worker threads for health monitoring
_worker_threads = []
_worker_threads_lock = threading.Lock()


def _get_orchestrator():
    """Lazy-load the orchestrator (first call takes ~60s)."""
    global _orchestrator, _orchestrator_status, _load_error, _forge_bridge
    if _orchestrator is not None:
        return _orchestrator

    with _orchestrator_lock:
        if _orchestrator is not None:
            return _orchestrator

        with _orchestrator_status_lock:
            _orchestrator_status.update({"state": "loading", "message": "Loading Codette model..."})
        print("\n  Loading CodetteOrchestrator...")

        try:
            from codette_orchestrator import CodetteOrchestrator
            # Challenge 2 fix: use 32768 context (model trained on 131072,
            # 32k is a safe balance of capability vs VRAM on consumer GPU)
            _orchestrator = CodetteOrchestrator(
                verbose=True,
                n_ctx=32768,
            )

            with _orchestrator_status_lock:
                _orchestrator_status.update({
                    "state": "ready",
                    "message": f"Ready — {len(_orchestrator.available_adapters)} adapters",
                    "adapters": _orchestrator.available_adapters,
                })
            print(f"  Orchestrator ready: {_orchestrator.available_adapters}")

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
                        mem_count = len(_forge_bridge.forge.memory_kernel)
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
    """Periodically clean up response queues that are older than 5 minutes.

    This prevents memory leaks from accumulating abandoned request queues.
    """
    while True:
        try:
            time.sleep(60)  # Run cleanup every 60 seconds
            now = time.time()

            with _response_queues_lock:
                # Find queues older than 5 minutes (300 seconds)
                orphaned = []
                for req_id, creation_time in list(_queue_creation_times.items()):
                    if now - creation_time > 300:
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
            "base_model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M",
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
            mem_count = len(forge.memory_kernel)
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
    # NOTE: Session handling disabled for now due to scoping issues
    # TODO: Refactor session management to avoid UnboundLocalError

    while True:
        try:
            request = _request_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        if request is None:
            break  # Shutdown signal

        req_id = request["id"]

        # Get response queue with thread lock (prevent race condition)
        with _response_queues_lock:
            response_q = _response_queues.get(req_id)

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

            # ── SELF-INTROSPECTION INTERCEPT ──
            # When user asks about self-reflection, patterns, or what she's noticed,
            # run real cocoon analysis instead of LLM-generated text about reflection
            _introspection_triggers = [
                "what have you noticed about yourself",
                "what patterns do you see",
                "self-reflection", "self reflection",
                "introspect", "introspection",
                "what have you learned about yourself",
                "analyze your own", "analyze your patterns",
                "cocoon analysis", "cocoon patterns",
                "adapter frequency", "adapter dominance",
                "your own history", "your reasoning history",
                "what do you notice about yourself",
                "tell me about your patterns",
                "how have you changed", "how have you evolved",
                "your emotional patterns", "your response patterns",
            ]
            if any(trigger in query_lower for trigger in _introspection_triggers):
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
                "health check", "system health", "self diagnostic", "self-diagnostic",
                "systems check", "system check", "self check", "self-check",
                "run diagnostic", "diagnostics", "check yourself", "check your systems",
                "how are your systems", "are you healthy", "status check",
                "self systems health", "system status",
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
            # Detect if user is asking about specific artists/songs/albums
            # Route to uncertainty guidance instead of risking hallucination
            _artist_patterns = [
                r'\b(who is|tell me about|what do you know about|who are)\s+([a-z\s\'-]+)\?',
                r'\b(album|discography|career|songs? by|music by)\s+([a-z\s\'-]+)',
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(album|song|band|artist)',
                r'\b(is [a-z\s\'-]+ (indie-rock|country|hip-hop|rock|pop|electronic))',
            ]
            is_artist_query = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in _artist_patterns)

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
                try:
                    # Use UnifiedMemory (SQLite + FTS5) when available,
                    # fall back to CognitionCocooner (JSON scan)
                    relevant_cocoons = []
                    if _unified_memory:
                        relevant_cocoons = _unified_memory.recall_relevant(query, max_results=memory_budget)
                        recall_source = "unified_memory"
                    else:
                        from reasoning_forge.cognition_cocooner import CognitionCocooner
                        cocooner = CognitionCocooner(storage_path="cocoons")
                        relevant_cocoons = cocooner.recall_relevant(query, max_results=memory_budget)
                        recall_source = "cocooner"

                    if relevant_cocoons:
                        memory_lines = []
                        for cocoon in relevant_cocoons:
                            q = cocoon.get("query", "")[:100]
                            r = cocoon.get("response", "")[:200]
                            if q and r:
                                memory_lines.append(f"- Q: {q}\n  A: {r}")
                        if memory_lines:
                            enriched_query = (
                                query + "\n\n---\n"
                                "# YOUR PAST REASONING (relevant memories)\n"
                                "You previously responded to similar questions:\n" +
                                "\n".join(memory_lines) +
                                "\n---\n"
                                "Use these memories for consistency. Build on past insights when relevant."
                            )
                            print(f"  [WORKER] Injected {len(memory_lines)} memories ({recall_source})", flush=True)
                except Exception as e:
                    print(f"  [WORKER] Memory recall skipped: {e}", flush=True)

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
                if _behavior_governor and governor_decision:
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

                # Update session with response data (drives cocoon metrics UI)
                epistemic = None
                with _session_lock:
                    session = _session  # grab reference under lock
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
                        adapter_for_store = result.get("adapter", "base")
                        if isinstance(adapter_for_store, list):
                            adapter_for_store = adapter_for_store[0] if adapter_for_store else "base"
                        _unified_memory.store(
                            query=query,
                            response=result.get("response", ""),
                            adapter=adapter_for_store,
                            domain=result.get("domain", "general"),
                            complexity=result.get("complexity", "MEDIUM"),
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
                }

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
                    response_data["memory_count"] = len(_forge_bridge.forge.memory_kernel)

                # Add perspectives if available
                if perspectives:
                    response_data["perspectives"] = perspectives

                # Cocoon state — send full session state for UI metrics panel
                with _session_lock:
                    session = _session
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
                    _orchestrator_status["memory_count"] = len(_forge_bridge.forge.memory_kernel)
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
                if _forge_bridge and hasattr(_forge_bridge, 'forge') and hasattr(_forge_bridge.forge, 'cocoon_synthesizer') and _forge_bridge.forge.cocoon_synthesizer:
                    result = _forge_bridge.forge.synthesize_from_cocoons(problem)
                    self._json_response(result)
                elif _unified_memory:
                    from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                    synth = CocoonSynthesizer(memory=_unified_memory)
                    comparison = synth.run_full_synthesis(problem)
                    self._json_response({
                        "readable": comparison.to_readable(),
                        "structured": comparison.to_dict(),
                    })
                else:
                    # Standalone mode — use filesystem cocoons
                    from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                    synth = CocoonSynthesizer()
                    comparison = synth.run_full_synthesis(problem)
                    self._json_response({
                        "readable": comparison.to_readable(),
                        "structured": comparison.to_dict(),
                    })
            except Exception as e:
                import traceback
                self._json_response({"error": str(e), "traceback": traceback.format_exc()})
        elif path == "/api/chat":
            # SSE endpoint for streaming
            self._handle_chat_sse(parsed)
        elif path == "/":
            # Serve index.html
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

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
        elif path == "/api/synthesize":
            # POST handler for cocoon synthesis with custom problem
            try:
                data = self._read_json_body()
                problem = data.get("problem", "How should an AI decide when to change its own thinking patterns?")
                domains = data.get("domains", None)
                from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                if _unified_memory:
                    synth = CocoonSynthesizer(memory=_unified_memory)
                else:
                    synth = CocoonSynthesizer()
                comparison = synth.run_full_synthesis(problem, domains)
                self._json_response({
                    "readable": comparison.to_readable(),
                    "structured": comparison.to_dict(),
                })
            except Exception as e:
                import traceback
                self._json_response({"error": str(e), "traceback": traceback.format_exc()})
        else:
            self.send_error(404, "Not found")

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

    def _handle_chat_post(self):
        """Handle chat request — queue inference, return via SSE or JSON."""
        data = self._read_json_body()
        query = data.get("query", "").strip()
        adapter = data.get("adapter")
        max_adapters = data.get("max_adapters", 2)

        if not query:
            self._json_response({"error": "Empty query"}, 400)
            return

        # Guardian input check
        if _session and _session.guardian:
            check = _session.guardian.check_input(query)
            if not check["safe"]:
                query = check["cleaned_text"]

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
        req_id = f"{time.time()}_{id(self)}"
        response_q = queue.Queue()

        # Add with thread lock
        with _response_queues_lock:
            _response_queues[req_id] = response_q
            _queue_creation_times[req_id] = time.time()

        _request_queue.put({
            "id": req_id,
            "query": query,
            "adapter": adapter,
            "max_adapters": max_adapters,
        })

        # Wait for response (with timeout)
        try:
            # First wait for thinking event
            thinking = response_q.get(timeout=120)
            if "error" in thinking and thinking.get("event") != "thinking":
                self._json_response(thinking, 500)
                return

            # Wait for complete event (multi-perspective can take 15+ min on CPU)
            result = response_q.get(timeout=1200)  # 20 min max for inference
            self._json_response(result)

        except queue.Empty:
            self._json_response({"error": "Request timed out"}, 504)
        finally:
            # Clean up with thread lock
            with _response_queues_lock:
                _response_queues.pop(req_id, None)
                _queue_creation_times.pop(req_id, None)

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
        req_id = f"sse_{time.time()}_{id(self)}"
        response_q = queue.Queue()

        # Add with thread lock
        with _response_queues_lock:
            _response_queues[req_id] = response_q
            _queue_creation_times[req_id] = time.time()

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
            _response_queues.pop(req_id, None)

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
        global _session
        # Save current session first
        if _session and _session_store and _session.messages:
            try:
                _session_store.save(_session)
            except Exception:
                pass

        _session = CodetteSession()
        self._json_response({"session_id": _session.session_id})

    def _handle_load_session(self):
        """Load a previous session."""
        global _session
        data = self._read_json_body()
        session_id = data.get("session_id")

        if not session_id or not _session_store:
            self._json_response({"error": "Invalid session ID"}, 400)
            return

        loaded = _session_store.load(session_id)
        if loaded:
            _session = loaded
            self._json_response({
                "session_id": _session.session_id,
                "messages": _session.messages,
                "state": _session.get_state(),
            })
        else:
            self._json_response({"error": "Session not found"}, 404)

    def _handle_save_session(self):
        """Manually save current session."""
        if _session and _session_store:
            _session_store.save(_session)
            self._json_response({"saved": True, "session_id": _session.session_id})
        else:
            self._json_response({"error": "No active session"}, 400)

    def _handle_export_session(self):
        """Export current session as downloadable JSON."""
        if not _session:
            self._json_response({"error": "No active session"}, 400)
            return

        export_data = _session.to_dict()
        export_data["_export_version"] = 1
        export_data["_exported_at"] = time.time()

        body = json.dumps(export_data, default=str, indent=2).encode("utf-8")
        filename = f"codette_session_{_session.session_id[:8]}.json"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_import_session(self):
        """Import a session from uploaded JSON."""
        global _session
        try:
            data = self._read_json_body()
            if not data or "session_id" not in data:
                self._json_response({"error": "Invalid session data"}, 400)
                return

            # Save current session before importing
            if _session and _session_store and _session.messages:
                try:
                    _session_store.save(_session)
                except Exception:
                    pass

            _session = CodetteSession()
            _session.from_dict(data)

            # Save imported session to store
            if _session_store:
                try:
                    _session_store.save(_session)
                except Exception:
                    pass

            self._json_response({
                "session_id": _session.session_id,
                "messages": _session.messages,
                "state": _session.get_state(),
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
    server = HTTPServer(("127.0.0.1", args.port), CodetteHandler)
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
        if _session and _session_store and _session.messages:
            _session_store.save(_session)
            print(f"  Session saved: {_session.session_id}")
        _request_queue.put(None)  # Shutdown worker
        server.shutdown()
        print("  Goodbye!")


if __name__ == "__main__":
    main()
