"""Benchmark: Codette Crawler vs the provided starter agent."""
import sys
sys.path.insert(0, ".")
from kaggle_environments import make
import main as m
from random import choice as rchoice

# Starter bot (from competition AGENTS.md)
def starter_agent(obs, config):
    actions = {}
    width = config.width
    my_robots = {uid: data for uid, data in obs.robots.items() if data[4] == obs.player}
    for uid, data in my_robots.items():
        rtype, col, row, energy = data[0], data[1], data[2], data[3]
        build_cd = data[7] if len(data) > 7 else 0
        idx = (row - obs.southBound) * width + col
        w = obs.walls[idx] if 0 <= idx < len(obs.walls) and obs.walls[idx] != -1 else 0
        if rtype == 0:
            if w & 1:
                actions[uid] = "JUMP_NORTH"
            elif energy >= config.workerCost and build_cd == 0:
                actions[uid] = "BUILD_WORKER"
            else:
                actions[uid] = "NORTH"
        elif rtype == 2 and (w & 1) and energy >= config.wallRemoveCost:
            actions[uid] = "REMOVE_NORTH"
        else:
            passable = []
            if not (w & 1): passable.append("NORTH")
            if not (w & 2): passable.append("EAST")
            if not (w & 4): passable.append("SOUTH")
            if not (w & 8): passable.append("WEST")
            actions[uid] = "NORTH" if "NORTH" in passable else (rchoice(passable) if passable else "IDLE")
    return actions

N = 20
wins = losses = draws = 0
for seed in range(N):
    m._S = None
    env = make("crawl", configuration={"randomSeed": seed}, debug=False)
    env.run(["main.py", starter_agent])
    final = env.steps[-1]
    r0 = final[0].reward
    r1 = final[1].reward
    if r0 > r1:
        wins += 1
        result = "WIN"
    elif r0 < r1:
        losses += 1
        result = "LOSS"
    else:
        draws += 1
        result = "DRAW"
    print(f"seed={seed:2d}  us={r0:8.1f}  starter={r1:8.1f}  {result}")

pct = wins * 100 // N
print(f"\nWin/Loss/Draw: {wins}/{losses}/{draws}  ({pct}% win rate over {N} games)")
