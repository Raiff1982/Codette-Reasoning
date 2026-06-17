#!/usr/bin/env python3
"""Memory telemetry for Codette — measures what she actually needs and uses.

Two tools:

1. MemoryTracker — context manager with a background peak sampler.
   Wrap any phase (model load, adapter swap, generation) and get back
   baseline, peak, delta, and duration as data, not prints.

       with MemoryTracker("generation") as mt:
           result = forge.generate(query)
       print(mt.report())          # human-readable
       stats = mt.to_dict()        # machine-readable

2. profile_server() — attaches to a running codette_server process by
   port/PID and samples its real RSS over a window, so you can watch
   what the live system consumes during actual requests.

Run standalone for a live system overview:
    python utilities/memory_telemetry.py            # snapshot of this machine
    python utilities/memory_telemetry.py --watch    # find + monitor codette_server
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil

_MB = 1024 * 1024
_GB = 1024 ** 3


@dataclass
class PhaseStats:
    """Memory stats for one tracked phase."""
    label: str
    baseline_mb: float = 0.0
    peak_mb: float = 0.0
    end_mb: float = 0.0
    duration_s: float = 0.0
    samples: int = 0

    @property
    def delta_mb(self) -> float:
        """Retained memory: what this phase kept after finishing."""
        return self.end_mb - self.baseline_mb

    @property
    def peak_delta_mb(self) -> float:
        """Transient memory: how far above baseline the phase spiked."""
        return self.peak_mb - self.baseline_mb

    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "baseline_mb": round(self.baseline_mb, 1),
            "peak_mb": round(self.peak_mb, 1),
            "end_mb": round(self.end_mb, 1),
            "retained_delta_mb": round(self.delta_mb, 1),
            "peak_delta_mb": round(self.peak_delta_mb, 1),
            "duration_s": round(self.duration_s, 2),
            "samples": self.samples,
        }


class MemoryTracker:
    """Context manager that tracks RSS baseline/peak/delta for a code phase.

    A daemon sampler thread polls RSS at `sample_interval` seconds so short
    transient spikes inside the phase are captured, not just the endpoints.
    """

    def __init__(self, label: str = "phase", sample_interval: float = 0.05,
                 pid: Optional[int] = None):
        self.stats = PhaseStats(label=label)
        self._interval = sample_interval
        self._process = psutil.Process(pid or os.getpid())
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._t0 = 0.0

    def _rss_mb(self) -> float:
        return self._process.memory_info().rss / _MB

    def _sample_loop(self):
        while not self._stop.is_set():
            try:
                rss = self._rss_mb()
                if rss > self.stats.peak_mb:
                    self.stats.peak_mb = rss
                self.stats.samples += 1
            except psutil.Error:
                break
            self._stop.wait(self._interval)

    def __enter__(self) -> "MemoryTracker":
        self.stats.baseline_mb = self._rss_mb()
        self.stats.peak_mb = self.stats.baseline_mb
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self.stats.end_mb = self._rss_mb()
        if self.stats.end_mb > self.stats.peak_mb:
            self.stats.peak_mb = self.stats.end_mb
        self.stats.duration_s = time.monotonic() - self._t0
        return False  # never swallow exceptions

    def to_dict(self) -> Dict:
        return self.stats.to_dict()

    def report(self) -> str:
        s = self.stats
        return (
            f"[{s.label}] baseline={s.baseline_mb:.0f}MB "
            f"peak={s.peak_mb:.0f}MB (+{s.peak_delta_mb:.0f} transient) "
            f"retained={s.delta_mb:+.0f}MB "
            f"in {s.duration_s:.1f}s ({s.samples} samples)"
        )


# ---------------------------------------------------------------------------
# Live server profiling
# ---------------------------------------------------------------------------

def find_codette_processes() -> List[psutil.Process]:
    """Find running codette_server (and worker) processes."""
    found = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if "codette_server" in cmdline and "python" in (proc.info["name"] or "").lower():
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def profile_server(duration_s: float = 30.0, interval_s: float = 0.5) -> Dict:
    """Sample a running codette_server's memory for `duration_s` seconds.

    Returns per-process min/peak/mean RSS plus system context — enough to
    answer "how much does she actually need" under real load.
    """
    procs = find_codette_processes()
    if not procs:
        return {"error": "No codette_server process found. Start it first."}

    print(f"Found {len(procs)} codette process(es): {[p.pid for p in procs]}")
    print(f"Sampling for {duration_s:.0f}s at {interval_s}s intervals...\n")

    history: Dict[int, List[float]] = {p.pid: [] for p in procs}
    t_end = time.monotonic() + duration_s

    while time.monotonic() < t_end:
        for p in procs:
            try:
                history[p.pid].append(p.memory_info().rss / _MB)
            except psutil.Error:
                pass
        time.sleep(interval_s)

    vm = psutil.virtual_memory()
    out: Dict = {
        "system_total_gb": round(vm.total / _GB, 2),
        "system_used_pct": vm.percent,
        "processes": [],
    }
    for pid, samples in history.items():
        if not samples:
            continue
        out["processes"].append({
            "pid": pid,
            "min_mb": round(min(samples), 1),
            "peak_mb": round(max(samples), 1),
            "mean_mb": round(sum(samples) / len(samples), 1),
            "samples": len(samples),
        })
    return out


def system_snapshot() -> Dict:
    """One-shot view of current machine state."""
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "total_ram_gb": round(vm.total / _GB, 2),
        "available_ram_gb": round(vm.available / _GB, 2),
        "used_pct": vm.percent,
        "swap_used_gb": round(sw.used / _GB, 2),
        "cpu_count": psutil.cpu_count(logical=True),
    }


def main():
    parser = argparse.ArgumentParser(description="Codette memory telemetry")
    parser.add_argument("--watch", action="store_true",
                        help="Find and monitor a running codette_server")
    parser.add_argument("--duration", type=float, default=30.0,
                        help="Watch duration in seconds (default 30)")
    args = parser.parse_args()

    if args.watch:
        result = profile_server(duration_s=args.duration)
        if "error" in result:
            print(result["error"])
            return 1
        print(f"System: {result['system_total_gb']} GB total, {result['system_used_pct']}% used")
        for p in result["processes"]:
            print(f"  PID {p['pid']}: min={p['min_mb']}MB  mean={p['mean_mb']}MB  "
                  f"peak={p['peak_mb']}MB  ({p['samples']} samples)")
        return 0

    snap = system_snapshot()
    print("System snapshot:")
    for k, v in snap.items():
        print(f"  {k}: {v}")

    # Demo: track a small allocation to show the tracker works
    with MemoryTracker("demo-allocation") as mt:
        _buf = bytearray(50 * _MB)  # 50 MB
        time.sleep(0.3)
        del _buf
    print(f"\nTracker demo: {mt.report()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
