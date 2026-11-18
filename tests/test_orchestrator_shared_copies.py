"""codette_orchestrator.py (llama.cpp path) and codette_shared.py (openvino path)
carry copies of the same constraint helpers.

2026-11-18: one copy had missed a fix. The orchestrator's
extract_primary_user_query did not strip attached files, so a file saying "in 10
words" cut her answer on that path. It now delegates. These tests pin that, and
fail if the remaining copies drift apart in logic, so the next fix to one copy
cannot silently miss the other. The orchestrator imports llama_cpp, so its
functions are read by AST, not imported.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "inference"))

ORCH = ROOT / "inference" / "codette_orchestrator.py"
SHARED = ROOT / "inference" / "codette_shared.py"


def _logic(path, name):
    t = ast.parse(path.read_text(encoding="utf-8"))
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            body = n.body[1:] if isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) else n.body
            src = ast.unparse(ast.Module(body=body, type_ignores=[]))
            return src.replace("_re.", "re.")
    raise AssertionError(f"{name} missing from {path.name}")


def test_attached_file_text_is_not_read_as_the_users_constraint():
    t = ast.parse(ORCH.read_text(encoding="utf-8"))
    g = {}
    fn = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "extract_primary_user_query"]
    exec(compile(ast.Module(body=fn, type_ignores=[]), str(ORCH), "exec"), g)
    q = ("--- Attached File: notes.txt (40 B) ---\nSummarise in 10 words.\n--- End of File ---\n\n"
         "What do you think of these notes?")
    assert g["extract_primary_user_query"](q) == "What do you think of these notes?"


def test_the_remaining_copies_match_in_logic():
    for name in ("extract_constraints", "build_constraint_override"):
        assert _logic(ORCH, name) == _logic(SHARED, name), name


def test_enforce_constraints_copies_behave_the_same():
    import re
    import itertools

    def load(p):
        t = ast.parse(p.read_text(encoding="utf-8"))
        g = {"re": re, "_re": re}
        fn = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "enforce_constraints"]
        exec(compile(ast.Module(body=fn, type_ignores=[]), str(p), "exec"), g)
        return g["enforce_constraints"]
    a, b = load(ORCH), load(SHARED)
    replies = ["Yes. Because the data supports it. Also many other reasons apply here.",
               "Gravity is curvature. Mass tells space how to curve. Space tells mass how to move.",
               "The answer is forty-two and that is the final answer which",
               "- apples\n- pears\n- plums and the rest which"]
    base = {"max_words": None, "max_sentences": None, "brevity": False, "binary": False, "list_format": False}
    for r, c in itertools.product(replies, [{"binary": True}, {"max_words": 6}, {"max_sentences": 1},
                                            {"brevity": True}, {"list_format": True}]):
        assert a(r, {**base, **c}) == b(r, {**base, **c}), (r, c)
