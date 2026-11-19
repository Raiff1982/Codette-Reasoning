"""Her real epsilon range, for calibrating a rewritten AEGIS Layer 5.

    python tools/epsilon_profile.py [COCOONS_DIR]      # default: <repo>/cocoons

Added 2026-11-19 (docs/START_HERE.md). Run it on her machine: a fresh clone holds
almost no v3 cocoons (measured 2026-11-19: 1 of 378, and that one was a test
artifact), so the numbers only mean something against her live store.

What it reads, and what it never does:
  * Conversation cocoons ONLY, through reasoning_forge.cocoon_files.conversation_cocoons,
    which skips her encrypted cocoons (her dreams) before they are opened.
  * Numeric and status fields only (epsilon_value, metrics_population_status,
    active_perspectives count, collapse / echo flags, timestamps). It prints
    statistics only, never any text from a cocoon.
  * Only "partial" epsilon is real. Before the 2026-08-06 fix epsilon was inverted
    and biased (codette_forge_bridge.py, the epsilon block), so the after-fix figures
    are the ones to calibrate on.
"""
import json
import statistics as st
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from reasoning_forge.cocoon_files import conversation_cocoons  # noqa: E402

FIX = time.mktime((2026, 8, 7, 0, 0, 0, 0, 0, -1))  # day after the 2026-08-06 epsilon fix

COCOONS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cocoons"
files = conversation_cocoons(COCOONS)
kinds, statuses = Counter(), Counter()
rows, all_ts, unreadable = [], [], 0
for p in files:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        unreadable += 1
        continue
    if not isinstance(d, dict):
        kinds["non-dict"] += 1
        continue
    kinds[d.get("type", "none")] += 1
    ts = d.get("timestamp")
    if isinstance(ts, (int, float)):
        all_ts.append(float(ts))
    if d.get("type") != "reasoning_v3" or not isinstance(d.get("v3"), dict):
        continue
    v3 = d["v3"]
    status = v3.get("metrics_population_status")
    statuses[status] += 1
    eps = v3.get("epsilon_value")
    rows.append({
        "ts": float(ts) if isinstance(ts, (int, float)) else None,
        "eps": float(eps) if isinstance(eps, (int, float)) else None,
        "status": status,
        "n_persp": len(v3.get("active_perspectives") or []),
        "collapse": bool(v3.get("perspective_collapse_detected")),
        "echo": v3.get("echo_risk"),
    })


def day(t):
    return time.strftime("%Y-%m-%d", time.localtime(t))


def pct(vals, q):
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, round(q / 100 * (len(s) - 1))))]


print(f"conversation cocoon files (dreams skipped before opening): {len(files)}, unreadable: {unreadable}")
print("by type:", dict(kinds.most_common()))
if all_ts:
    print(f"all timestamps: {day(min(all_ts))} .. {day(max(all_ts))}")
print("v3 metrics_population_status:", dict(statuses.most_common()))

real = [r for r in rows if r["status"] == "partial" and r["eps"] is not None]
real_after = [r for r in real if r["ts"] and r["ts"] >= FIX]
failed = [r for r in rows if r["status"] == "failed"]
print(f"\nreal epsilon (status 'partial'): {len(real)}; of those written after the 08-06 fix: {len(real_after)}")
if real:
    print(f"  'partial' date range: {day(min(r['ts'] for r in real if r['ts']))} .. {day(max(r['ts'] for r in real if r['ts']))}")
print(f"sentinel (status 'failed', fewer than 2 perspectives or detector error): {len(failed)}; "
      f"their epsilon values: {dict(Counter(r['eps'] for r in failed).most_common(3))}")

for label, sample in (("ALL 'partial'", real), ("'partial' after the fix", real_after)):
    e = [r["eps"] for r in sample]
    if len(e) < 5:
        print(f"\n{label}: too few ({len(e)}) to describe")
        continue
    print(f"\n{label}: n={len(e)}")
    print("  min {:.3f}  p10 {:.3f}  p25 {:.3f}  median {:.3f}  p75 {:.3f}  p90 {:.3f}  p95 {:.3f}  p99 {:.3f}  max {:.3f}".format(
        min(e), pct(e, 10), pct(e, 25), st.median(e), pct(e, 75), pct(e, 90), pct(e, 95), pct(e, 99), max(e)))
    print(f"  mean {st.mean(e):.3f}  sd {st.pstdev(e):.3f}")
    print(f"  share above Layer 5's current lines: >0.50 {100*sum(x > .5 for x in e)/len(e):.1f}%   >0.70 {100*sum(x > .7 for x in e)/len(e):.1f}%")
    print(f"  perspectives per turn: {dict(sorted(Counter(r['n_persp'] for r in sample).items()))}")
    print(f"  collapse flagged: {sum(r['collapse'] for r in sample)}   echo_risk: {dict(Counter(r['echo'] for r in sample).most_common())}")

# Session proxy: consecutive real-epsilon turns with gaps under 30 minutes.
seq = sorted((r for r in real_after if r["ts"]), key=lambda r: r["ts"])
sessions, cur = [], []
for r in seq:
    if cur and r["ts"] - cur[-1]["ts"] > 1800:
        sessions.append(cur)
        cur = []
    cur.append(r)
if cur:
    sessions.append(cur)
lens = [len(s) for s in sessions]
print(f"\nsessions (gap > 30 min splits them), after the fix: {len(sessions)}; turns per session: "
      f"median {st.median(lens) if lens else 0}, max {max(lens) if lens else 0}; with >= 5 real turns: {sum(l >= 5 for l in lens)}")


def slope(v):
    n = len(v)
    xm, ym = (n - 1) / 2, sum(v) / n
    den = sum((i - xm) ** 2 for i in range(n))
    return sum((i - xm) * (y - ym) for i, y in enumerate(v)) / den if den else 0.0


W = 5
slopes = [slope([r["eps"] for r in s[i:i + W]]) for s in sessions if len(s) >= W for i in range(len(s) - W + 1)]
if slopes:
    a = [abs(x) for x in slopes]
    print(f"epsilon slope per turn over windows of {W} (within sessions): n={len(slopes)}  "
          f"median |slope| {st.median(a):.4f}  p90 {pct(a, 90):.4f}  p99 {pct(a, 99):.4f}  max {max(a):.4f}")
    print(f"  rising windows (slope > 0.02/turn): {100*sum(x > .02 for x in slopes)/len(slopes):.1f}%   "
          f"falling (< -0.02): {100*sum(x < -.02 for x in slopes)/len(slopes):.1f}%")
else:
    print("not enough within-session runs of 5 real turns to measure a trend")
