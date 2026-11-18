"""media/: CodetteMediaEngine, extracted from the Movie_engine.py transcript (2026-11-18).

The original must stay byte-for-byte as it was; the extracted versions must parse;
and the main module must contain every class and method of the two lineage
versions, which is why it was chosen as the main one. moviepy is not part of
Codette's requirements, so the import check skips without it.
"""
import ast
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "media" / "codette_media_engine.py"
LINEAGE = sorted((ROOT / "media" / "lineage").glob("*.py"))


def _methods(path):
    t = ast.parse(path.read_text(encoding="utf-8"))
    return {f"{c.name}.{m.name}" for c in t.body if isinstance(c, ast.ClassDef)
            for m in c.body if isinstance(m, ast.FunctionDef)}


def test_the_transcript_is_untouched():
    digest = hashlib.sha256((ROOT / "Movie_engine.py").read_bytes()).hexdigest()
    assert digest == "1e50a740a0a8a160e8df643e8aa66cdf2ebe9ac3d7eb3222ddf7832f01c892d5"


def test_every_extracted_version_parses_and_keeps_its_docstring():
    assert len(LINEAGE) == 2
    for p in [MAIN, *LINEAGE]:
        t = ast.parse(p.read_text(encoding="utf-8"))
        assert (ast.get_docstring(t) or "").startswith("CodetteMediaEngine")
        assert " " not in p.read_text(encoding="utf-8")


def test_the_main_version_contains_the_lineage_versions():
    main = _methods(MAIN)
    for p in LINEAGE:
        assert _methods(p) <= main, p.name


def test_it_imports_with_moviepy_1():
    pytest.importorskip("moviepy.editor")
    import importlib.util as u
    spec = u.spec_from_file_location("codette_media_engine", MAIN)
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert hasattr(m, "CodetteMediaPipeline") and hasattr(m, "RenderPlan")
