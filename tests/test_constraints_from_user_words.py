"""Her answer is shaped by the user's constraints, never by her own notes.

2026-11-18, two faults on the OpenVINO path:

1. _synthesize calls generate() with the synthesis prompt, which quotes her lens
   notes. generate() read format constraints from that whole prompt, so a note
   saying "In short" made the merge brief, and "In one sentence" plus "yes or
   no" cut it to one sentence, as a yes/no answer, with a CRITICAL CONSTRAINT
   in her prompt. The user had asked for none of it.
2. The bridge's own user-constraint step imported codette_orchestrator, whose
   module-level `import llama_cpp` fails in openvino_env, so it never ran there.
   The 2026-07-05 rule: OV-path code imports codette_shared, never the
   orchestrator.

No model is loaded: generate() is replaced by a recorder (as in
test_synthesis_voice.py).
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "inference", ROOT / "openvino_backend"):
    sys.path.insert(0, str(p))

from openvino_backend.backend import OpenVINOBackend  # noqa: E402
from codette_shared import extract_constraints, extract_primary_user_query  # noqa: E402

NOTES = {
    "newton": "The answer is yes or no depending on the frame.",
    "davinci": "In one sentence: water follows the moon.",
}


@pytest.fixture(autouse=True)
def _no_embedder(monkeypatch):
    monkeypatch.setenv("CODETTE_MANIFOLD_STEER", "0")
    monkeypatch.delenv("CODETTE_SYNTH_BASE", raising=False)


def _backend():
    b = OpenVINOBackend.__new__(OpenVINOBackend)
    b._adapter_paths = {a: Path(a) for a in NOTES}
    b.calls = []

    def generate(query, adapter_name=None, system_prompt=None, **kw):
        b.calls.append({"query": query, **kw})
        return "merged", 1, []

    b.generate = generate
    return b


def test_the_merge_reads_constraints_from_the_users_question():
    b = _backend()
    b._synthesize("Explain how tides work.", dict(NOTES))
    call = b.calls[-1]
    assert call["constraint_query"] == "Explain how tides work."
    # The prompt it generates from still carries the notes; that is the point.
    assert "In one sentence" in call["query"]
    used = {k: v for k, v in extract_constraints(extract_primary_user_query(call["constraint_query"])).items() if v}
    leaked = {k: v for k, v in extract_constraints(extract_primary_user_query(call["query"])).items() if v}
    assert used == {}
    assert leaked, "the notes really do read as constraints; if not, this test no longer guards anything"


def test_generate_takes_its_constraints_from_constraint_query_when_given():
    src = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "generate")
    assert "constraint_query" in [a.arg for a in fn.args.args + fn.args.kwonlyargs]
    body = ast.unparse(fn)
    assert "extract_primary_user_query(constraint_query)" in body


OV_PATH = ["inference/codette_forge_bridge.py", "inference/codette_shared.py",
           "openvino_backend/backend.py"]


@pytest.mark.parametrize("rel", OV_PATH)
def test_ov_path_never_imports_the_llama_cpp_orchestrator(rel):
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    bad = [n.lineno for n in ast.walk(tree)
           if (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[-1] == "codette_orchestrator")
           or (isinstance(n, ast.Import) and any(a.name.split(".")[-1] == "codette_orchestrator" for a in n.names))]
    assert bad == [], f"{rel} imports codette_orchestrator at lines {bad}"
