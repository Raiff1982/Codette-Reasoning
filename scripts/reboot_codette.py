#!/usr/bin/env python3
"""Reboot Codette server cleanly and wait for her to come back up.

Usage:
    python scripts/reboot_codette.py                  # graceful stop + restart
    python scripts/reboot_codette.py --reinitialize   # + clear low-confidence cocoons
    python scripts/reboot_codette.py --port 7860      # custom port (default 7860)
    python scripts/reboot_codette.py --dry-run        # show what would happen, no action

The server takes ~80s to load the model on first start. This script waits up
to 180s for /api/health to confirm she's ready, then prints her status.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = ROOT / "inference" / "codette_server.py"
LOW_CONF_DIR = ROOT / "inference" / "cocoons" / "low_confidence"
ALT_LOW_CONF_DIR = ROOT / "cocoons" / "low_confidence"

HEALTH_TIMEOUT = 180   # seconds to wait for server to come up
HEALTH_INTERVAL = 5    # polling interval


def find_server_pid(port: int) -> list[int]:
    """Find PIDs of codette_server.py processes bound to port."""
    pids = []
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if parts:
                    try:
                        pids.append(int(parts[-1]))
                    except ValueError:
                        pass
    except Exception:
        pass
    return list(set(pids))


def kill_server(pids: list[int], dry_run: bool = False):
    """Kill server processes by PID."""
    if not pids:
        print("  No existing server process found.")
        return
    for pid in pids:
        print(f"  Stopping PID {pid}...")
        if not dry_run:
            try:
                os.kill(pid, signal.SIGTERM)
            except PermissionError:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                               capture_output=True)
            except ProcessLookupError:
                pass
    if not dry_run:
        time.sleep(3)


def clear_low_confidence(dry_run: bool = False):
    """Remove cocoons in low_confidence/ (they're flagged for review, not needed on fresh start)."""
    dirs = [d for d in [LOW_CONF_DIR, ALT_LOW_CONF_DIR] if d.exists()]
    if not dirs:
        print("  No low_confidence cocoon folder found — nothing to clear.")
        return
    for d in dirs:
        files = list(d.glob("*.json"))
        if not files:
            print(f"  {d.relative_to(ROOT)}: already empty.")
            continue
        print(f"  Clearing {len(files)} low-confidence cocoon(s) from {d.relative_to(ROOT)}/")
        if not dry_run:
            for f in files:
                f.unlink()


def start_server(port: int, dry_run: bool = False) -> subprocess.Popen | None:
    """Launch codette_server.py in a new visible console window."""
    python = sys.executable
    cmd = [python, str(SERVER_SCRIPT), "--port", str(port)]
    print(f"  Starting: {' '.join(cmd)}")
    if dry_run:
        return None
    if sys.platform == "win32":
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT / "inference"),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT / "inference"),
        )
    return proc


_HEALTHY_STATUSES = {"OK", "HEALTHY", "ok", "healthy"}


def wait_for_health(port: int, timeout: int = HEALTH_TIMEOUT) -> dict | None:
    """Poll /api/health until overall status is healthy or we time out.

    The server responds immediately (possibly with CRITICAL) while the model
    loads in the background.  We keep polling until it reports a healthy
    status so the caller always gets a post-load snapshot.
    """
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + timeout
    last_overall = "UNKNOWN"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                last_overall = data.get("overall", "UNKNOWN")
                if last_overall in _HEALTHY_STATUSES:
                    return data
                remaining = int(deadline - time.time())
                print(f"  Server up but status={last_overall}, waiting for model... ({remaining}s remaining)",
                      end="\r", flush=True)
        except (urllib.error.URLError, OSError):
            remaining = int(deadline - time.time())
            print(f"  Waiting for server... ({remaining}s remaining)", end="\r", flush=True)
        except Exception:
            pass
        time.sleep(HEALTH_INTERVAL)
    return None


def print_health(data: dict):
    overall = data.get("overall", "UNKNOWN")
    print(f"\n  Health: {overall}")
    checks = data.get("checks", {})
    for name, result in checks.items():
        status = result.get("status", "?") if isinstance(result, dict) else result
        print(f"    {name}: {status}")


def main():
    parser = argparse.ArgumentParser(description="Reboot Codette server")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--reinitialize", action="store_true",
                        help="Also clear low-confidence cocoons on restart")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show actions without executing them")
    args = parser.parse_args()

    dry = args.dry_run
    if dry:
        print("\n[DRY RUN — no changes will be made]\n")

    print(f"\nRebooting Codette (port {args.port})...")
    print("=" * 50)

    # 1. Find and stop existing server
    print("\n[1/4] Stopping existing server...")
    pids = find_server_pid(args.port)
    kill_server(pids, dry_run=dry)

    # 2. Optionally clear low-confidence cocoons
    if args.reinitialize:
        print("\n[2/4] Reinitializing — clearing low-confidence cocoons...")
        clear_low_confidence(dry_run=dry)
    else:
        print("\n[2/4] Skipping reinitialize (pass --reinitialize to clear low-confidence cocoons)")

    # 3. Start server
    print("\n[3/4] Starting server...")
    proc = start_server(args.port, dry_run=dry)

    if dry:
        print("\n[4/4] Health check skipped in dry-run mode.")
        print("\nDone (dry run).")
        return

    if proc is None:
        print("  Server process could not be started.")
        sys.exit(1)

    print(f"  PID {proc.pid} — server output visible in its own console window")

    # 4. Wait for health
    print(f"\n[4/4] Waiting for Codette to come up (up to {HEALTH_TIMEOUT}s)...")
    health = wait_for_health(args.port, timeout=HEALTH_TIMEOUT)

    print()
    print("=" * 50)
    if health:
        print_health(health)
        print("\n  Codette is ready.\n")
    else:
        print(f"\n  Server did not respond as HEALTHY within {HEALTH_TIMEOUT}s.")
        print(f"  Check the server console for startup errors.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
