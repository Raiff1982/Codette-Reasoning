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

import os, sys, json, time, threading, queue, argparse, webbrowser, traceback
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
            _orchestrator = CodetteOrchestrator(verbose=True)

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
                    _forge_bridge = CodetteForgeBridge(_orchestrator, use_phase6=True, use_phase7=True, verbose=True)
                    print(f"  Phase 6 bridge initialized")
                    print(f"  Phase 7 Executive Controller initialized")
                    with _orchestrator_status_lock:
                        _orchestrator_status.update({"phase6": "enabled", "phase7": "enabled"})
                except Exception as e:
                    print(f"  Phase 6/7 bridge failed (using lightweight routing): {e}")
                    import traceback
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
            adapter = request.get("adapter")  # None = auto-route
            max_adapters = request.get("max_adapters", 2)

            # Send "thinking" event
            try:
                response_q.put({"event": "thinking", "adapter": adapter or "auto"})
            except (queue.Full, RuntimeError) as e:
                print(f"  ERROR: Failed to queue thinking event: {e}")
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
                if _forge_bridge:
                    result = _forge_bridge.generate(query, adapter=adapter, max_adapters=max_adapters)
                else:
                    result = orch.route_and_generate(
                        query,
                        max_adapters=max_adapters,
                        strategy="keyword",
                        force_adapter=adapter if adapter and adapter != "auto" else None,
                    )

                # Update session DISABLED - session handling deferred
                # (was causing UnboundLocalError due to scoping issues)
                epistemic = None

                # Extract route info from result (if available from ForgeEngine)
                route = result.get("route")
                perspectives = result.get("perspectives", [])

                # Build response
                response_data = {
                    "event": "complete",
                    "response": result["response"],
                    "adapter": result.get("adapter",
                        result.get("adapters", ["base"])[0] if isinstance(result.get("adapters"), list) else "base"),
                    "confidence": route.get("confidence", 0) if isinstance(route, dict) else (route.confidence if route else 0),
                    "reasoning": route.get("reasoning", "") if isinstance(route, dict) else (route.reasoning if route else ""),
                    "tokens": result.get("tokens", 0),
                    "time": round(result.get("time", 0), 2),
                    "multi_perspective": route.get("multi_perspective", False) if isinstance(route, dict) else (route.multi_perspective if route else False),
                }

                # Add perspectives if available
                if perspectives:
                    response_data["perspectives"] = perspectives

                # Cocoon state DISABLED (requires session handling refactoring)

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

    # Start model loading in background
    threading.Thread(target=_get_orchestrator, daemon=True).start()

    # Wait for model to load (up to 120 seconds)
    print(f"  Waiting for model to load (this takes ~60s on first startup)...")
    start_wait = time.time()
    while True:
        with _orchestrator_status_lock:
            state = _orchestrator_status.get("state")
        if state not in ("idle", "loading"):
            break
        if time.time() - start_wait > 120:
            break
        time.sleep(0.5)

    with _orchestrator_status_lock:
        state = _orchestrator_status.get("state")
    if state == "ready":
        print(f"  Model loaded in {time.time() - start_wait:.0f}s")
    elif state == "loading":
        print(f"  Model still loading (will continue in background)...")
    else:
        print(f"  WARNING: Model load status: {_orchestrator_status}")

    # Start server
    server = HTTPServer(("127.0.0.1", args.port), CodetteHandler)
    url = f"http://localhost:{args.port}"
    print(f"\n  Server: {url}")
    print(f"  Press Ctrl+C to stop\n")

    # Open browser
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

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
