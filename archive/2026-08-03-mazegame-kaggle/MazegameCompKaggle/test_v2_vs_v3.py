"""Self-play: v3 (main.py) vs v2 saved copy (main_refloor_673.py)."""
import sys, importlib
sys.path.insert(0, ".")
from kaggle_environments import make

import main as v3
import importlib.util

spec = importlib.util.spec_from_file_location("v2", "main_refloor_673.py")
v2   = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

N = 40
v3_wins = v2_wins = draws = 0

for seed in range(N):
    v3._S = None
    v2._S = None
    env = make("crawl", configuration={"randomSeed": seed}, debug=False)
    # Alternate sides to cancel position bias
    if seed % 2 == 0:
        env.run(["main.py", v2.agent])
        r_v3 = env.steps[-1][0].reward
        r_v2 = env.steps[-1][1].reward
    else:
        env.run([v2.agent, "main.py"])
        r_v2 = env.steps[-1][0].reward
        r_v3 = env.steps[-1][1].reward

    if r_v3 > r_v2:
        v3_wins += 1; res = "V3 WIN"
    elif r_v2 > r_v3:
        v2_wins += 1; res = "V2 WIN"
    else:
        draws += 1; res = "DRAW"
    print(f"seed={seed:2d}  v3={r_v3:8.1f}  v2={r_v2:8.1f}  {res}")

pct = v3_wins * 100 // N
print(f"\nV3/V2/Draw: {v3_wins}/{v2_wins}/{draws}  ({pct}% v3 win rate over {N} games)")
