"""Her scratchpad stays out of our logs (Jonathan, 2026-09-28): every scratch_*
tool is logged by name only. Read from source so no model loads."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "inference"))
import codette_tools  # noqa: E402


def _set_literal(name):
    tree = ast.parse((ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise AssertionError(f"{name} not found")


def test_every_scratch_tool_is_kept_out_of_logs():
    registered = {n for n in codette_tools.ToolRegistry().tools if n.startswith("scratch")}
    assert registered, "no scratch tools registered?"
    assert registered <= _set_literal("SCRATCH_TOOLS")


def test_logging_sites_honour_scratch_tools():
    src = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    assert 'elif _name in PRIVATE_TOOLS or _name in SCRATCH_TOOLS:' in src
    assert src.count("_name in PRIVATE_TOOLS or _name in SCRATCH_TOOLS") >= 3
