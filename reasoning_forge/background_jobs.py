"""Report-only jobs that run on their own, off the request path.

`dream_cycle` (a nightly review of the day's conversation cocoons) and
`cocoon_self_trainer` (a shadow sentiment model trained on first-hand data) were
finished, tested and called by nothing: dream_cycle's docstring asked for a
Windows Task Scheduler entry that was never created, and the trainer had no
caller at all (docs/WIRING_STATE_2026-09-29.md, "finished work that runs
nowhere"). Registering a scheduled task would change the machine; a daemon
thread inside the server changes nothing outside it.

Rules for anything registered here:
  * report-only -- it may write a report or a shadow log, never her memory,
    prompts, routing or weights;
  * conversation cocoons only -- sweeping jobs go through
    reasoning_forge.cocoon_files so her encrypted cocoons are never opened;
  * what the runner itself keeps is timestamps and small counts, never text.

The runner starts after a delay (so it does not compete with model load on an
8 GB UMA machine), runs a job at most once per interval, survives restarts via a
small state file, and swallows exceptions into a status line so a failing job can
never reach a chat turn.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_STATE = Path(__file__).resolve().parent.parent / "data" / "background_jobs.json"


class BackgroundJobs:
    def __init__(self, jobs: Dict[str, Callable[[], dict]],
                 state_path: Optional[Path] = None,
                 interval_s: float = 86400.0, startup_delay_s: float = 600.0,
                 poll_s: float = 900.0):
        self.jobs = dict(jobs)
        self.state_path = Path(state_path) if state_path else DEFAULT_STATE
        self.interval_s = interval_s
        self.startup_delay_s = startup_delay_s
        self.poll_s = poll_s
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._state = self._load()

    # -- state ---------------------------------------------------------------
    def _load(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
            tmp.replace(self.state_path)
        except Exception as e:  # never reach a chat turn
            logger.warning("[background_jobs] could not save state: %s", e)

    # -- running -------------------------------------------------------------
    def due(self, name: str, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        last = (self._state.get(name) or {}).get("last_run")
        return last is None or (now - float(last)) >= self.interval_s

    def run_job(self, name: str) -> dict:
        """Run one job now. Records the outcome; never raises."""
        t0 = time.time()
        entry = dict(self._state.get(name) or {})
        try:
            summary = self.jobs[name]() or {}
            entry.update(ok=True, summary=summary, error=None)
        except Exception as e:
            entry.update(ok=False, error=f"{type(e).__name__}: {e}"[:300])
            logger.warning("[background_jobs] %s failed: %s", name, e)
        entry["last_run"] = t0
        entry["seconds"] = round(time.time() - t0, 2)
        entry["runs"] = int(entry.get("runs", 0)) + 1
        with self._lock:
            self._state[name] = entry
            self._save()
        return entry

    def run_due(self) -> list:
        ran = []
        for name in self.jobs:
            if self.due(name):
                self.run_job(name)
                ran.append(name)
        return ran

    def _loop(self) -> None:
        if self._stop.wait(self.startup_delay_s):
            return
        while not self._stop.is_set():
            try:
                self.run_due()
            except Exception as e:  # pragma: no cover - belt and braces
                logger.warning("[background_jobs] loop error: %s", e)
            if self._stop.wait(self.poll_s):
                return

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="background-jobs",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict:
        """What /api/health shows: when each job last ran and its counts. No text."""
        out = {}
        for name in self.jobs:
            e = self._state.get(name) or {}
            out[name] = {
                "status": ("NEVER_RUN" if not e else ("OK" if e.get("ok") else "FAILED")),
                "last_run": e.get("last_run"), "runs": e.get("runs", 0),
                "summary": e.get("summary"), "error": e.get("error"),
                "interval_hours": round(self.interval_s / 3600, 1),
            }
        return out


# -- the registered jobs -----------------------------------------------------

def _job_dream_cycle() -> dict:
    from reasoning_forge import dream_cycle
    return dream_cycle.run(days=1.0)


def _job_self_trainer() -> dict:
    from reasoning_forge.cocoon_self_trainer import CocoonSelfTrainer
    trainer = CocoonSelfTrainer()
    report, _shadow = trainer.train_shadow(
        cocoon_dir=Path(__file__).resolve().parent.parent / "cocoons")
    trainer.observe(report)         # data/self_train_shadow.jsonl, applied: false
    return {"collected": report.collected, "positive": report.positive,
            "negative": report.negative, "trained": report.trained,
            "reason": report.reason}


def _job_antibodies() -> dict:
    from reasoning_forge import antibodies
    return antibodies.job()


def default_jobs() -> Dict[str, Callable[[], dict]]:
    return {"dream_cycle": _job_dream_cycle, "cocoon_self_trainer": _job_self_trainer,
            "antibody_scan": _job_antibodies}
