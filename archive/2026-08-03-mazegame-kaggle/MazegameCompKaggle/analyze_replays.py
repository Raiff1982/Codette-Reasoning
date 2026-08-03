"""
Analyze downloaded replays to find economy patterns.
Focus: build orders, mine counts, terminal energy, robot counts per type.
"""
import json
from pathlib import Path
from collections import defaultdict

REPLAY_DIR = Path("J:/codette-clean/MazegameCompKaggle/replays")
FACTORY, SCOUT, WORKER, MINER = 0, 1, 2, 3
TYPE_NAME = {0: "factory", 1: "scout", 2: "worker", 3: "miner"}

# Sub IDs mapped to player labels
# bunterrrrr=53084625, Takahiro=53202279, ???=52806825 (1655), AI=52826626, Nicolas K=53265350
TOP_SUBS = {
    53084625: "bunterrrrr_2228",
    53202279: "Takahiro_1667",
    52806825: "anon_1655",
    53421538: "JiayiDu_1232",
    53010637: "Meenal_1167",
    53188991: "Henry_1332",
    52826626: "AI_1358",
    53265350: "Nicolas_1504",
    52547535: "NicB_1184",
    53311404: "Phillip_1256",
    53290495: "kaba777_1259",
    53409033: "Carter_1226",
    53460628: "anon2_1246",
    53480144: "us_671",
}

def analyze_replay(path):
    """Extract per-step stats for each player."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    rewards = d.get("rewards", [None, None])
    steps = d["steps"]
    n_steps = len(steps)

    # Figure out which player is which from globalRobots
    # We'll track stats for both players
    results = {}  # player_idx -> stats

    for pidx in [0, 1]:
        mine_counts = []
        robot_type_counts = []  # list of (step, {type: count})
        build_events = []       # (step, type)
        factory_energy = []
        worker_removal_steps = []

        prev_robots = {}  # uid -> type

        for si, step in enumerate(steps):
            # Prefer the observation that actually has game state (player 0's is typically complete)
            obs = None
            for try_pidx in [pidx, 1 - pidx]:
                candidate = step[try_pidx].get("observation") if isinstance(step[try_pidx], dict) else None
                if candidate and candidate.get("globalRobots"):
                    obs = candidate
                    break
            if not obs:
                continue

            all_robots = obs.get("globalRobots", {})
            mines = obs.get("globalMines", obs.get("mines", {}))

            # Robots belonging to this player
            my_robots = {uid: d for uid, d in all_robots.items() if d[4] == pidx}

            # Count by type
            type_counts = defaultdict(int)
            for uid, d_r in my_robots.items():
                type_counts[d_r[0]] += 1

            robot_type_counts.append((si, dict(type_counts)))

            # Factory energy
            fac = next((d_r for d_r in my_robots.values() if d_r[0] == FACTORY), None)
            if fac:
                factory_energy.append((si, fac[3]))

            # Build events: new UIDs that weren't there before
            cur_uids = set(my_robots.keys())
            prev_uids = set(prev_robots.keys())
            new_uids = cur_uids - prev_uids
            for uid in new_uids:
                rtype = my_robots[uid][0]
                if rtype != FACTORY:
                    build_events.append((si, rtype))

            # Mine count: mines owned by this player
            # Format varies: dict {"owner":N,...} or list [income, max, owner, ...]
            my_mines = 0
            for v in mines.values():
                if isinstance(v, dict):
                    if v.get("owner") == pidx:
                        my_mines += 1
                elif isinstance(v, list) and len(v) >= 3:
                    if v[2] == pidx:
                        my_mines += 1

            mine_counts.append((si, my_mines))

            # Worker removal events
            action = step[pidx].get("action", {}) if isinstance(step[pidx], dict) else {}
            if isinstance(action, dict):
                for uid, act in action.items():
                    if isinstance(act, str) and "REMOVE" in act and uid in my_robots:
                        if my_robots[uid][0] == WORKER:
                            worker_removal_steps.append(si)

            prev_robots = {uid: d_r[0] for uid, d_r in my_robots.items()}

        results[pidx] = {
            "reward": rewards[pidx] if pidx < len(rewards) else None,
            "mine_counts": mine_counts,
            "robot_type_counts": robot_type_counts,
            "build_events": build_events,
            "factory_energy": factory_energy,
            "worker_removal_steps": worker_removal_steps,
            "n_steps": n_steps,
        }

    return results


def summarize_player(stats):
    """Compute aggregate stats from per-step data."""
    builds = stats["build_events"]
    scout_builds  = [s for s, t in builds if t == SCOUT]
    worker_builds = [s for s, t in builds if t == WORKER]
    miner_builds  = [s for s, t in builds if t == MINER]

    # Peak mine count
    peak_mines = max((m for _, m in stats["mine_counts"]), default=0)
    # Mine count at step 100, 200
    m_at = {}
    for step_target in [50, 100, 150, 200, 300]:
        pts = [(s, m) for s, m in stats["mine_counts"] if s <= step_target]
        m_at[step_target] = pts[-1][1] if pts else 0

    # Terminal factory energy (last 5 steps)
    fe = stats["factory_energy"]
    terminal_fe = fe[-1][1] if fe else 0

    # Max factory energy ever
    max_fe = max((e for _, e in fe), default=0)

    # Step when first mine placed
    first_mine_step = None
    for s, m in stats["mine_counts"]:
        if m > 0:
            first_mine_step = s
            break

    return {
        "reward":       stats["reward"],
        "n_scouts":     len(scout_builds),
        "n_workers":    len(worker_builds),
        "n_miners":     len(miner_builds),
        "peak_mines":   peak_mines,
        "first_mine":   first_mine_step,
        "mines@100":    m_at[100],
        "mines@200":    m_at[200],
        "mines@300":    m_at[300],
        "terminal_fe":  terminal_fe,
        "max_fe":       max_fe,
        "n_removals":   len(stats["worker_removal_steps"]),
        "build_order":  " ".join(TYPE_NAME[t] for _, t in builds[:8]),
        "n_steps":      stats["n_steps"],
    }


# ── Run analysis ──────────────────────────────────────────────────────────────
all_summaries = []  # (player_label, summary)

replay_files = sorted(REPLAY_DIR.glob("*.json"))
print(f"Analyzing {len(replay_files)} replays...\n")

for fpath in replay_files:
    try:
        results = analyze_replay(fpath)
        for pidx, stats in results.items():
            label = f"player{pidx}"
            s = summarize_player(stats)
            all_summaries.append((label, fpath.name, s))
    except Exception as e:
        print(f"  ERROR {fpath.name}: {e}")

# ── Aggregate by reward tier ──────────────────────────────────────────────────
def print_group(name, summaries):
    if not summaries:
        return
    n = len(summaries)
    avg = lambda key: sum(s[key] or 0 for _, _, s in summaries) / n
    pct_workers = sum(1 for _, _, s in summaries if s["n_workers"] > 0) / n * 100
    print(f"\n{'='*60}")
    print(f"{name}  (n={n} player-episodes)")
    print(f"  avg reward:     {avg('reward'):8.0f}")
    print(f"  avg scouts:     {avg('n_scouts'):6.1f}")
    print(f"  avg workers:    {avg('n_workers'):6.1f}  ({pct_workers:.0f}% games built >=1)")
    print(f"  avg miners:     {avg('n_miners'):6.1f}")
    print(f"  peak mines:     {avg('peak_mines'):6.1f}")
    print(f"  mines@100:      {avg('mines@100'):6.1f}")
    print(f"  mines@200:      {avg('mines@200'):6.1f}")
    print(f"  terminal_fe:    {avg('terminal_fe'):8.0f}")
    print(f"  avg removals:   {avg('n_removals'):6.1f}")
    print(f"  avg steps:      {avg('n_steps'):6.0f}")
    # Most common build orders
    from collections import Counter
    orders = Counter(s["build_order"] for _, _, s in summaries)
    print("  top build orders:")
    for order, cnt in orders.most_common(5):
        print(f"    [{cnt:2d}x] {order}")

# Split into top (reward ≥1300) vs mid vs low
top_tier    = [(lbl, fn, s) for lbl, fn, s in all_summaries if (s["reward"] or 0) >= 1300]
mid_tier    = [(lbl, fn, s) for lbl, fn, s in all_summaries if 700 <= (s["reward"] or 0) < 1300]
our_tier    = [(lbl, fn, s) for lbl, fn, s in all_summaries if 0 < (s["reward"] or 0) < 700]
neg_tier    = [(lbl, fn, s) for lbl, fn, s in all_summaries if (s["reward"] or 0) <= 0]

print_group("TOP TIER (≥1300)", top_tier)
print_group("MID TIER (700–1300)", mid_tier)
print_group("OUR TIER (<700)", our_tier)
print_group("LOST (<= 0)", neg_tier)

# ── Detailed bunterrrrr games ─────────────────────────────────────────────────
print(f"\n{'='*60}")
print("BUNTERRRRR detail (highest reward games)")
bunter_games = sorted([(fn, s) for _, fn, s in all_summaries if (s["reward"] or 0) > 2000],
                      key=lambda x: -(x[1]["reward"] or 0))
for fn, s in bunter_games[:10]:
    print(f"  {fn}: rew={s['reward']:.0f}  scouts={s['n_scouts']} workers={s['n_workers']} miners={s['n_miners']}  mines@100={s['mines@100']} mines@200={s['mines@200']}  peak={s['peak_mines']}  bo=[{s['build_order']}]")

# ── Mine count timeline comparison ───────────────────────────────────────────
print(f"\n{'='*60}")
print("MINE TIMELINE (avg mines at each checkpoint)")
print(f"{'step':>6}  {'top≥1300':>10}  {'mid700-1300':>12}  {'us<700':>8}")
for step_t in [50, 100, 150, 200, 300]:
    key = f"mines@{step_t}" if step_t in [100, 200, 300] else None
    if key is None:
        continue
    t_avg = sum(s[key] or 0 for _, _, s in top_tier) / max(1, len(top_tier))
    m_avg = sum(s[key] or 0 for _, _, s in mid_tier) / max(1, len(mid_tier))
    o_avg = sum(s[key] or 0 for _, _, s in our_tier) / max(1, len(our_tier))
    print(f"  @{step_t:3d}  {t_avg:10.2f}  {m_avg:12.2f}  {o_avg:8.2f}")
