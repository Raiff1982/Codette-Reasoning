"""
Download and analyze Maze Crawler replays.
Finds top-player submissions via API probing, then downloads & analyzes replays.
"""
import json, time, requests
from pathlib import Path
from collections import defaultdict

TOKEN_FILE = Path.home() / ".kaggle" / "access_token"
KAGGLE_JSON = Path.home() / ".kaggle" / "kaggle.json"

def get_auth():
    if TOKEN_FILE.exists():
        return {"Authorization": f"Bearer {TOKEN_FILE.read_text().strip()}"}, None
    creds = json.loads(KAGGLE_JSON.read_text())
    return {}, (creds["username"], creds["key"])

HEADERS, AUTH = get_auth()
BASE = "https://www.kaggle.com/api/v1"
COMP = "maze-crawler"
OUT  = Path("J:/codette-clean/MazegameCompKaggle/replays")
OUT.mkdir(exist_ok=True)

def get(path, params=None):
    r = requests.get(f"{BASE}/{path}", headers=HEADERS, auth=AUTH,
                     params=params, timeout=30)
    return r.json() if r.ok else None

def episodes_for_sub(sid):
    d = get(f"competitions/submissions/{sid}/episodes")
    return d.get("episodes", []) if d else []

def download_replay(eid):
    dest = OUT / f"{eid}.json"
    if dest.exists():
        return dest
    r = requests.get(f"{BASE}/competitions/episodes/{eid}/replay",
                     headers=HEADERS, auth=AUTH, timeout=60)
    if r.ok:
        dest.write_bytes(r.content)
        return dest
    return None

# ── Leaderboard ───────────────────────────────────────────────────────────────
lb = get(f"competitions/{COMP}/leaderboard/view")
top = lb["submissions"][:20]
top_by_tid = {str(t["teamId"]): t for t in top}

print("Top 10 teams:")
for t in top[:10]:
    name = t["teamName"].encode("ascii","replace").decode()
    print(f"  {name:35s} score={t['score']:>8}")

# ── Find sub IDs by probing team API endpoints ─────────────────────────────────
print("\nLooking up submission IDs for top teams...")
top_subs = {}  # teamId -> (submissionId, name, score)

for t in top[:15]:
    tid = str(t["teamId"])
    name = t["teamName"].encode("ascii","replace").decode()
    score = t["score"]

    # Try direct team submission lookup
    for endpoint in [
        f"competitions/{COMP}/teams/{tid}/submissions",
        f"competitions/teams/{tid}/submissions",
        f"teams/{tid}/competitions/{COMP}/submissions",
    ]:
        d = get(endpoint)
        if d:
            print(f"  HIT {endpoint}: {str(d)[:100]}")
            break

    # Try to get team's episodes directly
    for endpoint in [
        f"competitions/{COMP}/teams/{tid}/episodes",
        f"competitions/teams/{tid}/episodes",
    ]:
        d = get(endpoint)
        if d:
            print(f"  HIT {endpoint}: {str(d)[:100]}")
            break
    time.sleep(0.1)

# ── Alternative: scrape recent competition episodes ───────────────────────────
print("\nSearching for competition-wide episode list...")
for endpoint in [
    f"competitions/{COMP}/episodes",
    f"competitions/episodes?competition={COMP}",
    f"competitions/{COMP}/simulations",
    f"competitions/{COMP}/leaderboard/episodes",
]:
    d = get(endpoint)
    if d:
        print(f"  HIT: {endpoint}")
        print(f"  keys: {list(d.keys()) if isinstance(d, dict) else type(d)}")
        if isinstance(d, list):
            print(f"  first: {d[0] if d else 'empty'}")

# ── Last resort: use known sub IDs near ours to find top players ─────────────
# Our sub IDs are ~53480144, 53481023. Top players submitted around May-June.
# Scan a range of submission IDs and check if they belong to top teams.
print("\nScanning submission ID space for top teams...")
# Top player scores were set in May-early June. Sub IDs are sequential.
# Let's sample some IDs near known sub IDs to find top players.
# The #1 player bunterrrrr submitted 2026-05-27 — earlier than ours.
# Their sub ID should be lower. Let's try some ranges.

found_top = {}
# Try a range around known opponent subs
known_subs = [52260643, 52873859, 53241029, 53103064, 53412585, 52952496, 53402288, 53229653, 53092792]
print("Checking known opponent subs for chain to top players...")
for osid in known_subs:
    oeps = episodes_for_sub(osid)
    for ep in oeps:
        for ag in ep.get("agents", []):
            tid = str(ag.get("teamId", ""))
            if tid in top_by_tid and tid not in found_top:
                sid = ag.get("submissionId")
                if sid:
                    found_top[tid] = (sid, top_by_tid[tid]["teamName"].encode("ascii","replace").decode(), top_by_tid[tid]["score"])
                    print(f"  FOUND: {found_top[tid][1]} sub={sid} score={found_top[tid][2]}")
    time.sleep(0.15)

print(f"\nFound {len(found_top)} top players via chain")

# ── Download replays for found top players + our own ─────────────────────────
all_replays = []

for tid, (sid, name, score) in found_top.items():
    eps = episodes_for_sub(sid)
    print(f"\n{name} (score={score}): {len(eps)} eps")
    for ep in eps[:8]:
        eid = ep["id"]
        f = download_replay(eid)
        if f:
            all_replays.append((name, float(score), f))
            print(f"  dl {eid}")
        time.sleep(0.1)

# Our episodes
OUR_SUB = 53480144
our_eps = episodes_for_sub(OUR_SUB)
for ep in our_eps[:10]:
    f = download_replay(ep["id"])
    if f:
        all_replays.append(("us_671", 671, f))

print(f"\nTotal replays downloaded: {len(all_replays)}")
print(f"Files in {OUT}:")
for p in sorted(OUT.iterdir()):
    print(f"  {p.name} ({p.stat().st_size//1024}KB)")
