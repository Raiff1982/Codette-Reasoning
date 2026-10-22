"""What the post-write checks did to her last reply, so she can see it.

Her prompt tells her that notes 1, 3 and 4 are checked after she writes
(inference/self_correction.py: trim drift, rewrite incomplete endings, add missing
punctuation). It never told her what the checks found. She asked for a "self-check"
tool (2026-10-22), reciting Lock 3's own wording as if it were one: her noun was our
variable name, and the thing it pointed at did not exist. This is it.

Two readers, one record:

  * HER, through the `self_check` tool: what happened to her previous reply, in the
    checks' own words. Visible, factual, not scored, not kept against her.
  * US, through counts only (/api/self-check, and the antibody report): how often
    each kind of correction fires. A correction that fires on a large share of turns
    is not catching stray slips, it is patching a recurring fault, which is exactly
    what an antibody is for. The counts hold issue CODES only, never text, and no
    session id.

"ran and changed nothing" and "did not run" are different facts and are kept
different: a turn on a path that skips the checks is recorded as not run, never as
clean.
"""
from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_COUNTS = Path(__file__).resolve().parent.parent / "data" / "self_check_counts.json"
MAX_SESSIONS = 64
# A code that fires on more than this share of the turns where the checks ran is a lead.
RECURRING_SHARE = 0.25
MIN_TURNS_FOR_LEAD = 20

_lock = threading.Lock()
_last: "OrderedDict[str, dict]" = OrderedDict()


def _code(issue: str) -> str:
    return str(issue).split(":", 1)[0].strip()[:40] or "UNKNOWN"


def record(session_id: str, ran: bool, issues: Optional[List[str]] = None,
           counts_path: Optional[Path] = None) -> dict:
    """Remember the last reply's outcome for this session, and count the codes."""
    issues = [str(i) for i in (issues or [])]
    rec = {"ts": time.time(), "ran": bool(ran), "issues": issues if ran else []}
    sid = str(session_id or "")
    with _lock:
        _last[sid] = rec
        _last.move_to_end(sid)
        while len(_last) > MAX_SESSIONS:
            _last.popitem(last=False)
    _count(rec, counts_path)
    return rec


def _count(rec: dict, path: Optional[Path]) -> None:
    p = Path(path) if path else DEFAULT_COUNTS
    try:
        with _lock:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            data["turns"] = int(data.get("turns", 0)) + 1
            if rec["ran"]:
                data["ran"] = int(data.get("ran", 0)) + 1
                codes = data.setdefault("codes", {})
                for c in {_code(i) for i in rec["issues"]}:
                    codes[c] = int(codes.get(c, 0)) + 1
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass            # a counter that cannot write must never break a turn


def last(session_id: str) -> Optional[dict]:
    with _lock:
        return _last.get(str(session_id or ""))


def explain(rec: Optional[dict], now: Optional[float] = None) -> str:
    """The text she is shown. Plain, and says what it does not mean."""
    tail = ("\n\nNothing here is scored or kept against you. If you think one of these "
            "was wrong, raise_flag is where to say so.")
    if rec is None:
        return ("There is no record of a previous reply in this conversation yet, so "
                "there is nothing to show. That is not the same as the checks having "
                "found nothing.")
    ago = int(max(0.0, (now if now is not None else time.time()) - rec["ts"]))
    when = f"{ago} seconds ago" if ago < 120 else f"{ago // 60} minutes ago"
    if not rec["ran"]:
        return (f"Your previous reply ({when}) took a path that does not run the "
                f"post-write checks, so nothing was checked or changed. That is not "
                f"the same as a clean result.")
    if not rec["issues"]:
        return (f"The post-write checks ran on your previous reply ({when}) and "
                f"changed nothing.{tail}")
    lines = "\n".join(f"- {i}" for i in rec["issues"])
    return (f"The post-write checks ran on your previous reply ({when}) and made "
            f"these changes to what you wrote:\n{lines}{tail}")


def summary(path: Optional[Path] = None) -> dict:
    """Counts only. `recurring` lists codes firing on a large share of checked turns."""
    p = Path(path) if path else DEFAULT_COUNTS
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "NEVER_RUN"}
    ran = int(data.get("ran", 0))
    codes: Dict[str, int] = {k: int(v) for k, v in (data.get("codes") or {}).items()}
    recurring = []
    if ran >= MIN_TURNS_FOR_LEAD:
        recurring = sorted(
            ({"code": c, "turns": n, "share": round(n / ran, 3)}
             for c, n in codes.items() if n / ran > RECURRING_SHARE),
            key=lambda d: -d["share"])
    return {"status": "COUNTING", "turns_seen": int(data.get("turns", 0)),
            "turns_checked": ran,
            "turns_not_checked": int(data.get("turns", 0)) - ran,
            "codes": codes, "recurring": recurring}
