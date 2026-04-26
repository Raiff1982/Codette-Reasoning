"""Execute the Kaggle notebook with the Windows asyncio fix applied first."""
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Fix Windows Proactor loop incompatibility with ZMQ before anything else loads
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import nbformat
from nbclient import NotebookClient

NB_PATH = "F:/codettes-scoring-engine.ipynb"

print("Loading notebook...")
with open(NB_PATH, encoding="utf-8") as f:
    nb = nbformat.read(f, as_version=4)

print(f"Executing {len(nb.cells)} cells...")
client = NotebookClient(
    nb,
    timeout=900,
    kernel_name="python3",
    resources={"metadata": {"path": "J:/codette-clean"}},
)

with client.setup_kernel():
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        preview = "".join(cell.source).strip().splitlines()[0][:60]
        print(f"  [{i:02d}] {preview}...", end=" ", flush=True)
        try:
            client.execute_cell(cell, i)
            # Grab first output line if any
            out_line = ""
            for o in cell.get("outputs", []):
                txt = "".join(o.get("text", [])).strip().splitlines()
                if txt:
                    out_line = txt[0][:60]
                    break
                if o.get("output_type") == "error":
                    out_line = f"ERROR: {o.get('ename')}: {o.get('evalue','')[:40]}"
                    break
            print(f"OK  {out_line}")
        except Exception as e:
            print(f"FAIL: {e}")

print("\nSaving...")
with open(NB_PATH, "w", encoding="utf-8") as f:
    nbformat.write(nb, f)
print("Done.")
