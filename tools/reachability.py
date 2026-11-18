"""Which live Python files can be reached by imports from the entry points.

    python3 tools/reachability.py inference/codette_server.py inference/codette_chat_ui.py mcp/codette_mcp.py api/rest_skin.py

Added 2026-11-18 (docs/WIRING_STATE_2026-11-18.md). Follows every import, including
ones inside functions and try blocks, and string imports via importlib. Reads
Python source only: never her stores. Set OUT=path.json to save the result.
"""
import ast, os, re, subprocess, sys, json
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(root)
LIVE = ("inference", "reasoning_forge", "openvino_backend", "Protection_Layer", "consciousness", "ethics", "api")
files = subprocess.run(["git", "ls-files"] + [f"{d}/*.py" for d in LIVE], capture_output=True, text=True).stdout.split()
files += ["mcp/codette_mcp.py"]
files += [f for f in subprocess.run(["git", "ls-files", "*.py"], capture_output=True, text=True).stdout.split() if "/" not in f]
by_base = {}
for f in files:
    b = os.path.basename(f)[:-3]
    if b == "__init__": b = os.path.basename(os.path.dirname(f))
    by_base.setdefault(b, []).append(f)
def refs(f):
    try: t = ast.parse(open(f, encoding="utf-8", errors="replace").read())
    except SyntaxError: return set()
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            for a in n.names: out.update(a.name.split("."))
        elif isinstance(n, ast.ImportFrom):
            if n.module: out.update(n.module.split("."))
            for a in n.names: out.add(a.name)          # from pkg import module
        elif isinstance(n, ast.Call):
            fn = n.func; nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if nm in ("import_module", "__import__", "spec_from_file_location") and n.args:
                for a in n.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        out.update(re.split(r"[./\\]", a.value.replace(".py", "")))
    return out
graph = {f: {g for r in refs(f) for g in by_base.get(r, []) if g != f} for f in files}
roots = sys.argv[1:]
seen, stack = set(roots), list(roots)
while stack:
    for g in graph[stack.pop()]:
        if g not in seen: seen.add(g); stack.append(g)
unreached = sorted(set(files) - seen)
if os.environ.get("OUT"):
    json.dump({"reached": sorted(seen), "unreached": unreached}, open(os.environ["OUT"], "w"), indent=1)
for f in unreached: print("  unreached:", f)
print(len(files), "files;", len(seen), "reachable from roots;", len(unreached), "not")
