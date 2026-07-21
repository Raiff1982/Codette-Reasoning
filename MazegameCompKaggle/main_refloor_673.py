"""
Codette Crawler v2 — Multi-Perspective Maze Bot
===============================================
Five reasoning perspectives per turn:
  1. Survival     — factory stays above scroll, safe jump bounds
  2. Economy      — build priority: scout > miner > worker
  3. Exploration  — scouts fan out toward mining nodes
  4. Infrastructure — workers clear path 4+ rows ahead
  5. Mining       — miners find nodes and TRANSFORM

Bugs fixed vs v1:
  - JUMP_NORTH now checks northBound (was killing us by jumping off map)
  - Factory uses BFS to route around walls instead of idling
  - Workers flee factory's crush radius when factory can move
"""
from collections import deque
from random import choice

_S = None

FACTORY, SCOUT, WORKER, MINER = 0, 1, 2, 3

DELTA = {"NORTH": (0, 1), "SOUTH": (0, -1), "EAST": (1, 0), "WEST": (-1, 0)}
BIT   = {"NORTH": 1, "EAST": 2, "SOUTH": 4, "WEST": 8}
DIRS  = list(DELTA)


def _walled(walls, c, r, d):
    """True if wall exists (or cell unknown). Unknown cells treated as walled."""
    return bool(walls.get((c, r), 0b1111) & BIT[d])


def _free(walls, c, r):
    return [d for d in DIRS if not _walled(walls, c, r, d)]


def _bfs(walls, src, dst, limit=80):
    """First move from src toward dst through known walls. Returns None if unreachable."""
    if src == dst:
        return "IDLE"
    prev = {src: (None, None)}
    q = deque([(src, 0)])
    while q:
        (c, r), depth = q.popleft()
        if depth >= limit:
            continue
        for d, (dc, dr) in DELTA.items():
            if _walled(walls, c, r, d):
                continue
            nxt = (c + dc, r + dr)
            if nxt in prev:
                continue
            prev[nxt] = ((c, r), d)
            if nxt == dst:
                cur = nxt
                while prev[cur][0] != src:
                    cur = prev[cur][0]
                return prev[cur][1]
            q.append((nxt, depth + 1))
    return None


def _factory_nav(walls, fc, fr, nb):
    """Best move for factory to make northward progress.

    Tries direct north, then BFS to nearest cell with open north,
    then falls back to south (backtrack) to find alternate route.
    nb = northBound (exclusive — landing at nb destroys factory).
    """
    # Direct north
    if not _walled(walls, fc, fr, "NORTH"):
        return "NORTH"

    # BFS: find nearest reachable cell that has north open AND jump won't overshoot
    visited = {(fc, fr)}
    q = deque([(fc, fr, 0)])
    best = None
    while q:
        c, r, depth = q.popleft()
        if depth > 10:
            break
        for d, (dc, dr) in DELTA.items():
            if _walled(walls, c, r, d):
                continue
            nc, nr = c + dc, r + dr
            if (nc, nr) in visited:
                continue
            visited.add((nc, nr))
            if not _walled(walls, nc, nr, "NORTH"):
                best = (nc, nr)
                break
            q.append((nc, nr, depth + 1))
        if best:
            break

    if best:
        mv = _bfs(walls, (fc, fr), best, 12)
        if mv:
            return mv

    # Last resort: go south to escape a dead end (only if safe distance allows it)
    return "IDLE"


def _factory_nav_retreat(walls, fc, fr):
    """Like _factory_nav but allows going south — use only when well above boundary."""
    if not _walled(walls, fc, fr, "NORTH"):
        return "NORTH"
    visited = {(fc, fr)}
    q = deque([(fc, fr, 0)])
    best = None
    while q:
        c, r, depth = q.popleft()
        if depth > 10:
            break
        for d, (dc, dr) in DELTA.items():
            if _walled(walls, c, r, d):
                continue
            nc, nr = c + dc, r + dr
            if (nc, nr) in visited:
                continue
            visited.add((nc, nr))
            if not _walled(walls, nc, nr, "NORTH"):
                best = (nc, nr)
                break
            q.append((nc, nr, depth + 1))
        if best:
            break
    if best:
        mv = _bfs(walls, (fc, fr), best, 12)
        if mv:
            return mv
    if not _walled(walls, fc, fr, "SOUTH"):
        return "SOUTH"
    return "IDLE"


def _scroll_interval(step, cfg):
    s0   = getattr(cfg, "scrollStartInterval", 4)
    s1   = getattr(cfg, "scrollEndInterval",   1)
    ramp = getattr(cfg, "scrollRampSteps",    400)
    if step >= ramp:
        return float(s1)
    return s0 - (s0 - s1) * step / ramp


def agent(obs, config):
    global _S
    if _S is None:
        _S = {
            "step":      0,
            "walls":     {},
            "mines":     {},
            "nodes":     {},   # remembered mining nodes
            "miner_tgt": {},
            "w":         config.width,
        }

    _S["step"] += 1
    step = _S["step"]
    sb = obs.southBound
    nb = obs.northBound   # exclusive top — landing AT nb destroys unit
    W  = _S["w"]

    # ── Absorb observations into persistent memory ────────────────────────────
    for i, v in enumerate(obs.walls):
        if v != -1:
            _S["walls"][(i % W, sb + i // W)] = v
    for k, d in obs.mines.items():
        c, r = map(int, k.split(","))
        _S["mines"][(c, r)] = d
    for k in obs.miningNodes:
        c, r = map(int, k.split(","))
        _S["nodes"][(c, r)] = True
    for pos in list(_S["nodes"]):   # prune nodes consumed by mines
        if pos in _S["mines"]:
            del _S["nodes"][pos]

    vis_nodes = {tuple(map(int, k.split(","))): 1 for k in obs.miningNodes}

    # ── Classify robots ───────────────────────────────────────────────────────
    my      = {u: d for u, d in obs.robots.items() if d[4] == obs.player}
    fac     = next(((u, d) for u, d in my.items() if d[0] == FACTORY), None)
    scouts  = {u: d for u, d in my.items() if d[0] == SCOUT}
    workers = {u: d for u, d in my.items() if d[0] == WORKER}
    miners  = {u: d for u, d in my.items() if d[0] == MINER}

    act = {}
    inv = _scroll_interval(step, config)

    # ══════════════════════════════════════════════════════════════════════════
    # PERSPECTIVE 1 + 2 — SURVIVAL & ECONOMY  (Factory)
    # ══════════════════════════════════════════════════════════════════════════
    if fac:
        fu, fd = fac
        fc, fr, fe = fd[1], fd[2], fd[3]
        fmove_cd = fd[5] if len(fd) > 5 else 0
        fj_cd    = fd[6] if len(fd) > 6 else 20
        fb_cd    = fd[7] if len(fd) > 7 else 0

        safe     = fr - sb
        urgent   = safe <= max(3, inv * 2.5)
        critical = safe <= 2

        n_wall  = _walled(_S["walls"], fc, fr, "NORTH")
        free_f  = _free(_S["walls"], fc, fr)

        # Jump is safe only if landing stays within the map
        can_jump_north = fj_cd == 0 and (fr + 2) < nb
        can_jump_south = fj_cd == 0 and (fr - 2) > sb

        spawn_occ = any(
            d[1] == fc and d[2] == fr + 1
            for u, d in my.items() if d[0] != FACTORY
        )

        # ── Critical: survive — NEVER go south ───────────────────────────────
        if critical:
            if can_jump_north:
                act[fu] = "JUMP_NORTH"
            elif "NORTH" in free_f:
                act[fu] = "NORTH"
            else:
                # No jump, no north: push toward center to break oscillation
                sides = [o for o in free_f if o in ("EAST", "WEST")]
                if sides:
                    preferred = "EAST" if fc < W // 2 else "WEST"
                    act[fu] = preferred if preferred in sides else sides[0]
                else:
                    act[fu] = "IDLE"

        # ── North wall + safe jump available → jump ──────────────────────────
        elif n_wall and can_jump_north:
            act[fu] = "JUMP_NORTH"

        # ── Urgent: route north aggressively ─────────────────────────────────
        elif urgent:
            if "NORTH" in free_f:
                act[fu] = "NORTH"
            elif can_jump_north:
                act[fu] = "JUMP_NORTH"
            else:
                act[fu] = _factory_nav(_S["walls"], fc, fr, nb)

        # ── Normal + north open: consider building ────────────────────────────
        elif not n_wall:
            if fb_cd == 0 and not spawn_occ:
                ns  = len(scouts)
                nw  = len(workers)
                nm  = len(miners)
                n_m = len(_S["mines"])
                nds = _S["nodes"]

                if ns == 0 and fe >= config.scoutCost:
                    act[fu] = "BUILD_SCOUT"
                elif nm == 0 and n_m == 0 and nds and fe >= config.minerCost:
                    act[fu] = "BUILD_MINER"
                elif ns < 2 and fe >= config.scoutCost:
                    act[fu] = "BUILD_SCOUT"
                elif nm < 2 and nds and fe >= config.minerCost and fe > 400:
                    act[fu] = "BUILD_MINER"
                elif nw < 1 and fe >= config.workerCost and fe > 600 and step > 60:
                    act[fu] = "BUILD_WORKER"
                elif ns < 4 and fe >= config.scoutCost:
                    act[fu] = "BUILD_SCOUT"
                else:
                    act[fu] = "NORTH"
            else:
                act[fu] = "NORTH"

        # ── Normal + north wall: BFS route around it ─────────────────────────
        else:
            if safe > 8:
                act[fu] = _factory_nav_retreat(_S["walls"], fc, fr)
            else:
                act[fu] = _factory_nav(_S["walls"], fc, fr, nb)

    # ══════════════════════════════════════════════════════════════════════════
    # PERSPECTIVE 3 — EXPLORATION  (Scouts)
    # ══════════════════════════════════════════════════════════════════════════
    for uid, d in scouts.items():
        c, r, e = d[1], d[2], d[3]
        if e == 0:
            act[uid] = "IDLE"
            continue

        # Transfer energy to factory if about to be scrolled off
        if r <= sb + 2 and fac:
            fc_f, fr_f = fac[1][1], fac[1][2]
            for dn, (dc, dr) in DELTA.items():
                if (c + dc, r + dr) == (fc_f, fr_f) and not _walled(_S["walls"], c, r, dn):
                    act[uid] = f"TRANSFER_{dn}"
                    break
            else:
                opts = _free(_S["walls"], c, r)
                act[uid] = "NORTH" if "NORTH" in opts else (choice(opts) if opts else "IDLE")
            continue

        # Head toward nearest known mining node
        nds = _S["nodes"]
        if nds:
            tgt = min(nds, key=lambda p: abs(p[0] - c) + abs(p[1] - r))
            mv  = _bfs(_S["walls"], (c, r), tgt, 70)
            if mv and mv != "IDLE":
                act[uid] = mv
                continue

        # Explore: north-biased random walk
        opts = _free(_S["walls"], c, r)
        if r > sb + 3:
            opts = [o for o in opts if o != "SOUTH"] or opts
        if opts:
            act[uid] = choice(opts + (["NORTH"] * 2 if "NORTH" in opts else []))
        else:
            act[uid] = "IDLE"

    # ══════════════════════════════════════════════════════════════════════════
    # PERSPECTIVE 4 — INFRASTRUCTURE  (Workers)
    # ══════════════════════════════════════════════════════════════════════════
    for uid, d in workers.items():
        c, r, e = d[1], d[2], d[3]
        if e == 0:
            act[uid] = "IDLE"
            continue

        # Transfer energy if about to be scrolled off
        if r <= sb + 2 and fac:
            fc_f, fr_f = fac[1][1], fac[1][2]
            for dn, (dc, dr) in DELTA.items():
                if (c + dc, r + dr) == (fc_f, fr_f) and not _walled(_S["walls"], c, r, dn):
                    act[uid] = f"TRANSFER_{dn}"
                    break
            else:
                opts = _free(_S["walls"], c, r)
                act[uid] = "NORTH" if "NORTH" in opts else (choice(opts) if opts else "IDLE")
            continue

        if fac:
            fc_f  = fac[1][1]
            fr_f  = fac[1][2]
            fmv   = fac[1][5] if len(fac[1]) > 5 else 0
            fac_moves = (fmv == 0)
            ahead = r - fr_f

            # Crush danger: factory is about to move into our cell
            if c == fc_f and ahead <= 1 and fac_moves:
                opts = _free(_S["walls"], c, r)
                safe_opts = [o for o in opts if o != "SOUTH"]
                act[uid] = "NORTH" if "NORTH" in opts else (choice(safe_opts) if safe_opts else choice(opts) if opts else "IDLE")
                continue

            # In position (≥4 ahead in same column): clear walls then advance
            if c == fc_f and ahead >= 4:
                if _walled(_S["walls"], c, r, "NORTH") and e >= config.wallRemoveCost:
                    act[uid] = "REMOVE_NORTH"
                    continue
                act[uid] = "NORTH"
                continue

            # Navigate to 4 rows ahead in factory's column
            tgt = (fc_f, fr_f + 4)
            mv  = _bfs(_S["walls"], (c, r), tgt, 40)
            if mv and mv != "IDLE":
                act[uid] = mv
                continue

        # Generic: go north
        opts = _free(_S["walls"], c, r)
        go   = [o for o in opts if o != "SOUTH"] or opts
        act[uid] = "NORTH" if "NORTH" in opts else (choice(go) if go else "IDLE")

    # ══════════════════════════════════════════════════════════════════════════
    # PERSPECTIVE 5 — MINING  (Miners)
    # ══════════════════════════════════════════════════════════════════════════
    for uid, d in miners.items():
        c, r, e = d[1], d[2], d[3]
        if e == 0:
            act[uid] = "IDLE"
            continue

        # Transfer energy if about to be scrolled off
        if r <= sb + 2 and fac:
            fc_f, fr_f = fac[1][1], fac[1][2]
            for dn, (dc, dr) in DELTA.items():
                if (c + dc, r + dr) == (fc_f, fr_f) and not _walled(_S["walls"], c, r, dn):
                    act[uid] = f"TRANSFER_{dn}"
                    break
            else:
                opts = _free(_S["walls"], c, r)
                act[uid] = "NORTH" if "NORTH" in opts else (choice(opts) if opts else "IDLE")
            continue

        # Transform if standing on a visible mining node
        if (c, r) in vis_nodes and e >= config.transformCost:
            act[uid] = "TRANSFORM"
            _S["miner_tgt"].pop(uid, None)
            continue

        # Navigate to nearest remembered mining node
        nds = _S["nodes"]
        if nds:
            tgt = _S["miner_tgt"].get(uid)
            if tgt not in nds:
                tgt = min(nds, key=lambda p: abs(p[0] - c) + abs(p[1] - r))
                _S["miner_tgt"][uid] = tgt
            mv = _bfs(_S["walls"], (c, r), tgt, 80)
            if mv and mv != "IDLE":
                act[uid] = mv
                continue

        # Explore north looking for nodes
        opts = _free(_S["walls"], c, r)
        if r > sb + 3:
            opts = [o for o in opts if o != "SOUTH"] or opts
        act[uid] = "NORTH" if "NORTH" in opts else (choice(opts) if opts else "IDLE")

    # ── Fallback ──────────────────────────────────────────────────────────────
    for uid in my:
        if uid not in act:
            act[uid] = "IDLE"

    return act
