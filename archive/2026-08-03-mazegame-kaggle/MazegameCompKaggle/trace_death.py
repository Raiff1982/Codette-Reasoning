"""Trace a losing game to find why v3 factory dies."""
import sys
sys.path.insert(0, ".")
import main
from kaggle_environments import make

_TRACE = []
_orig = main.agent
_S0 = [None]

def tracing_agent(obs, config):
    act = _orig(obs, config)
    if main._S:
        step = main._S["step"]
        sb = obs.southBound
        nb = obs.northBound
        my = {u: d for u, d in obs.robots.items() if d[4] == obs.player and d[0] == 0}
        if my:
            fu, fd = next(iter(my.items()))
            fc, fr, fe = fd[1], fd[2], fd[3]
            fmv = fd[5] if len(fd) > 5 else 0
            fj  = fd[6] if len(fd) > 6 else 0
            fb  = fd[7] if len(fd) > 7 else 0
            safe = fr - sb
            inv = main._scroll_interval(step, config)
            uth = max(3, inv * 2.5)
            nm = len([d for u, d in obs.robots.items() if d[4] == obs.player and d[0] == 3])
            fa = act.get(fu, "?")
            _TRACE.append(f"s{step:3d} r={fr:2d} safe={safe:2.0f}(th={uth:.0f}) nb={nb} fe={fe:4d} fmv={fmv} fj={fj:2d} fb={fb:2d} nm={nm} act={fa}")
    return act

main.agent = tracing_agent

for seed in [0, 1, 7]:
    main._S = None
    _TRACE.clear()
    env = make("crawl", configuration={"randomSeed": seed}, debug=False)
    env.run([tracing_agent, "main.py"])
    r0 = env.steps[-1][0].reward
    r1 = env.steps[-1][1].reward
    total = len(env.steps)
    print(f"\n{'='*70}")
    print(f"Seed={seed}  v3={r0}  v2={r1}  steps={total}")
    print(f"{'='*70}")
    for line in _TRACE[:100]:
        flag = " <<BUILD" if "BUILD" in line else ""
        flag += " !!SOUTH" if "SOUTH" in line and "JUMP" not in line else ""
        print(line + flag)
    print("...")
