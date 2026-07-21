"""Trace factory actions for seed=3 to verify oscillation fix and early builds."""
import sys, json, tempfile, os
sys.path.insert(0, ".")

# Monkey-patch the agent to write a debug trace
import main

_ORIG_AGENT = main.agent
_TRACE = []
_MAX_STEPS = 60

def tracing_agent(obs, config):
    act = _ORIG_AGENT(obs, config)
    step = main._S["step"] if main._S else -1
    if step <= _MAX_STEPS and main._S:
        sb = obs.southBound
        # Find factory in local obs (player's own)
        my = {u: d for u, d in obs.robots.items() if d[4] == obs.player and d[0] == 0}
        if my:
            fu, fd = next(iter(my.items()))
            fc, fr, fe = fd[1], fd[2], fd[3]
            fmv = fd[5] if len(fd) > 5 else 0
            fj  = fd[6] if len(fd) > 6 else 0
            fb  = fd[7] if len(fd) > 7 else 0
            safe = fr - sb
            inv = main._scroll_interval(step, config)
            urgent_th = max(3, inv * 2.5)
            factory_act = act.get(fu, "?")
            _TRACE.append(f"step {step:3d}: row={fr:2d} safe={safe:3.0f}(th={urgent_th:.0f})"
                          f"  fmv_cd={fmv}  fj_cd={fj:2d}  fb_cd={fb}"
                          f"  fe={fe:4d}  act={factory_act}")
    return act

main.agent = tracing_agent
sys.modules["main"].agent = tracing_agent

from kaggle_environments import make

main._S = None
env = make("crawl", configuration={"randomSeed": 3}, debug=False)
env.run([tracing_agent, "main.py"])
r0 = env.steps[-1][0].reward
r1 = env.steps[-1][1].reward

print(f"Seed=3 rewards: p0={r0}  p1={r1}")
print()
print("Factory trace (first 60 steps):")
for line in _TRACE:
    flag = ""
    if "BUILD" in line:
        flag = "  <<< BUILD"
    elif "SOUTH" in line:
        flag = "  <<< SOUTH"
    print(line + flag)

builds = [l for l in _TRACE if "BUILD" in l]
print(f"\nTotal builds in first {_MAX_STEPS} steps: {len(builds)}")
for b in builds:
    print(" ", b)
