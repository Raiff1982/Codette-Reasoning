"""Benchmark: Codette Crawler vs random across N seeds."""
import sys
sys.path.insert(0, ".")
from kaggle_environments import make
import main as m

N = 30
wins = losses = draws = 0
for seed in range(N):
    m._S = None
    env = make("crawl", configuration={"randomSeed": seed}, debug=False)
    env.run(["main.py", "random"])
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
    print(f"seed={seed:2d}  us={r0:8.1f}  random={r1:8.1f}  {result}")

pct = wins * 100 // N
print(f"\nWin/Loss/Draw: {wins}/{losses}/{draws}  ({pct}% win rate over {N} games)")
