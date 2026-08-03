"""Print raw factory data around death to verify field indices."""
import sys
sys.path.insert(0, ".")
from kaggle_environments import make
import main as m

m._S = None
env = make("crawl", configuration={"randomSeed": 5}, debug=False)
env.run(["main.py", "random"])

death_step = None
for i, step in enumerate(env.steps):
    obs = step[0].observation
    if not obs or not hasattr(obs, "robots"):
        continue
    if not any(v[0] == 0 and v[4] == 0 for v in obs.robots.values()):
        death_step = i
        break

for j in range(max(0, death_step - 4), death_step + 1):
    obs = env.steps[j][0].observation
    action = env.steps[j][0].action
    if not obs or not hasattr(obs, "robots"):
        continue
    for uid, data in obs.robots.items():
        if data[0] == 0 and data[4] == 0:  # our factory
            print(f"step={j} uid={uid} raw={list(data)} sb={obs.southBound} nb={obs.northBound}")
            print(f"       action={action}")
            print(f"       type={data[0]} col={data[1]} row={data[2]} energy={data[3]} owner={data[4]}")
            if len(data) > 5: print(f"       data[5]={data[5]}  data[6]={data[6] if len(data)>6 else 'N/A'}  data[7]={data[7] if len(data)>7 else 'N/A'}")
