"""The model-card publisher (tools/publish_model_card.py) and its workflow
(.github/workflows/publish-model-card.yml). Added 2026-11-20.

Nothing here talks to the real Hub. A fake `huggingface_hub` records what would be
sent. The workflow tests read the YAML and hold it to the rules in the script's
docstring: manual only, main only, read-only permissions, the secret visible to one
step, nothing typed into the form reaching a shell.
"""
import hashlib
import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "publish_model_card.py"
WORKFLOW = ROOT / ".github" / "workflows" / "publish-model-card.yml"
TOKEN = "tok-SECRET-do-not-print-123"


def _load():
    spec = importlib.util.spec_from_file_location("publish_model_card", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def P():
    return _load()


def _fake_hub(tmp_path, served=None, oid="rev123", upload_error=None):
    """A stand-in for huggingface_hub. `served` is what the Hub hands back on download
    (default: exactly what it was sent)."""
    calls = {}
    mod = types.ModuleType("huggingface_hub")

    class HfApi:
        def __init__(self, token=None):
            calls["token"] = token

        def upload_file(self, **kw):
            if upload_error:
                raise upload_error
            calls["upload"] = kw
            return types.SimpleNamespace(oid=oid) if oid else types.SimpleNamespace()

    def hf_hub_download(**kw):
        calls["download"] = kw
        p = tmp_path / "served.md"
        p.write_bytes(served if served is not None else calls["upload"]["path_or_fileobj"])
        return str(p)

    mod.HfApi, mod.hf_hub_download = HfApi, hf_hub_download
    return mod, calls


def _root_with_card(tmp_path, content, as_bytes=False):
    d = tmp_path / "training" / "model_cards"
    d.mkdir(parents=True)
    f = d / "empathy_v4_README.md"
    f.write_bytes(content) if as_bytes else f.write_text(content, encoding="utf-8")
    return tmp_path


# ── what it sends ──────────────────────────────────────────────────────────

def test_the_real_card_loads_and_its_hash_is_the_files(P):
    data, digest = P.load_card("empathy_v4")
    on_disk = (ROOT / "training" / "model_cards" / "empathy_v4_README.md").read_bytes()
    assert data == on_disk and digest == hashlib.sha256(on_disk).hexdigest()


def test_upload_sends_the_exact_bytes_to_the_fixed_destination(P, tmp_path, monkeypatch, capsys):
    fake, calls = _fake_hub(tmp_path)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    assert P.main(["empathy_v4", "--provenance", "run 42 at abc"]) == 0
    up = calls["upload"]
    assert up["repo_id"] == "Raiff1982/codette-adapters-v4" and up["repo_type"] == "model"
    assert up["path_in_repo"] == "empathy/README.md"
    assert up["path_or_fileobj"] == (ROOT / "training/model_cards/empathy_v4_README.md").read_bytes()
    assert "run 42 at abc" in up["commit_description"] and calls["token"] == TOKEN
    assert calls["download"]["revision"] == "rev123"          # verified at the revision just written
    out = capsys.readouterr()
    assert "published and verified at revision rev123" in out.out


def test_the_token_never_reaches_the_output(P, tmp_path, monkeypatch, capsys):
    fake, _ = _fake_hub(tmp_path)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    P.main(["empathy_v4"])
    seen = capsys.readouterr()
    assert TOKEN not in seen.out + seen.err


def test_an_error_that_quotes_the_token_is_scrubbed(P, tmp_path, monkeypatch, capsys):
    fake, _ = _fake_hub(tmp_path, upload_error=RuntimeError(f"401 for {TOKEN}"))
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    assert P.main(["empathy_v4"]) == 5
    seen = capsys.readouterr()
    assert TOKEN not in seen.out + seen.err and "***" in seen.err


def test_a_copy_that_differs_on_the_hub_fails_the_run(P, tmp_path, monkeypatch, capsys):
    fake, _ = _fake_hub(tmp_path, served=b"something else")
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    assert P.main(["empathy_v4"]) == 4
    assert "NOT VERIFIED" in capsys.readouterr().err


def test_without_a_commit_id_it_verifies_main(P, tmp_path, monkeypatch):
    fake, calls = _fake_hub(tmp_path, oid=None)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    assert P.main(["empathy_v4"]) == 0 and calls["download"]["revision"] == "main"


# ── what stops it ──────────────────────────────────────────────────────────

def test_no_token_stops_before_the_hub_is_touched(P, tmp_path, monkeypatch, capsys):
    fake, calls = _fake_hub(tmp_path)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert P.main(["empathy_v4"]) == 3
    assert calls == {} and "HF_TOKEN" in capsys.readouterr().err


def test_dry_run_needs_no_token_and_never_imports_the_client(P, monkeypatch, capsys):
    class Boom(types.ModuleType):
        def __getattr__(self, name):
            raise AssertionError("a dry run must not use the Hub client")
    monkeypatch.setitem(sys.modules, "huggingface_hub", Boom("huggingface_hub"))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert P.main(["empathy_v4", "--dry-run"]) == 0
    out = capsys.readouterr().out
    digest = hashlib.sha256((ROOT / "training/model_cards/empathy_v4_README.md").read_bytes()).hexdigest()
    assert digest[:16] in out and "nothing was sent" in out
    assert "hf://models/Raiff1982/codette-adapters-v4/empathy/README.md" in out


def test_only_listed_cards_can_be_named(P):
    with pytest.raises(SystemExit) as e:
        P.main(["not_a_card"])
    assert e.value.code == 2
    for name, c in P.CARDS.items():
        assert c["source"].startswith("training/model_cards/") and (ROOT / c["source"]).is_file()
        assert c["repo_id"].startswith("Raiff1982/") and c["path_in_repo"].endswith("README.md")
        assert c["repo_type"] == "model"


def test_a_source_outside_the_card_folder_is_refused(P, monkeypatch):
    monkeypatch.setitem(P.CARDS, "sneaky", dict(P.CARDS["empathy_v4"], source="tools/publish_model_card.py"))
    with pytest.raises(P.Refused, match="not inside"):
        P.load_card("sneaky")


def test_text_shaped_like_a_credential_is_refused_and_not_shown(P, tmp_path):
    secret = "hf_" + "A" * 34
    root = _root_with_card(tmp_path, f"---\nx: y\n---\n# card\nkey {secret}\n")
    with pytest.raises(P.Refused) as e:
        P.load_card("empathy_v4", root)
    assert secret not in str(e.value) and "credential" in str(e.value)


@pytest.mark.parametrize("content,as_bytes,why", [
    ("", False, "empty"),
    ("# no front matter\n", False, "front matter"),
    ("---\nnever closed\n# body\n", False, "front matter"),
    (b"---\n\xff\xfe\n---\n", True, "UTF-8"),
    ("---\na: b\n---\n" + "x" * 200_001, False, "limit"),
])
def test_cards_that_are_not_cards_are_refused(P, tmp_path, content, as_bytes, why):
    root = _root_with_card(tmp_path, content, as_bytes=as_bytes)
    with pytest.raises(P.Refused, match=why):
        P.load_card("empathy_v4", root)


# ── the workflow file ──────────────────────────────────────────────────────

def _wf():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return doc, doc.get("on", doc.get(True))                 # YAML 1.1 reads a bare `on` as True


def test_the_workflow_is_manual_only_and_read_only():
    doc, on = _wf()
    assert set(on) == {"workflow_dispatch"}                  # no push, pull_request(_target), schedule
    assert doc["permissions"] == {"contents": "read"}
    assert "env" not in doc and "env" not in doc["jobs"]["publish"]


def test_the_job_runs_only_from_main_with_a_timeout():
    job = _wf()[0]["jobs"]["publish"]
    assert job["if"] == "github.ref == 'refs/heads/main'" and job["timeout-minutes"] <= 15


def test_the_secret_is_named_once_and_only_in_the_publish_step():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert len(re.findall(r"secrets\.", text)) == 1 and "secrets.HF_TOKEN" in text
    steps = _wf()[0]["jobs"]["publish"]["steps"]
    holders = [s["name"] for s in steps if "secrets." in str(s.get("env", {}))]
    assert holders == ["Publish"]


def test_nothing_typed_into_the_form_reaches_a_shell():
    for s in _wf()[0]["jobs"]["publish"]["steps"]:
        assert "${{" not in s.get("run", ""), s["name"]      # inputs go through env, never into run


def test_the_workflow_uses_only_first_party_actions_and_keeps_no_git_credentials():
    steps = _wf()[0]["jobs"]["publish"]["steps"]
    assert all(s["uses"].startswith("actions/") for s in steps if "uses" in s)
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"]["persist-credentials"] is False


def test_the_form_offers_exactly_the_cards_the_script_allows(P):
    on = _wf()[1]
    assert on["workflow_dispatch"]["inputs"]["card"]["options"] == sorted(P.CARDS)


# ── shadow rules: nothing live uses it, and the antibodies are clear ───────

def test_nothing_live_imports_the_publisher():
    live = ["inference", "reasoning_forge", "openvino_backend", "Protection_Layer",
            "consciousness", "ethics", "api", "mcp"]
    offenders = [str(f.relative_to(ROOT)) for d in live for f in (ROOT / d).rglob("*.py")
                 if "publish_model_card" in f.read_text(encoding="utf-8", errors="replace")]
    assert offenders == [], offenders


def test_the_antibodies_find_nothing_in_the_publisher(tmp_path):
    from reasoning_forge import antibodies as A
    import shutil
    shutil.copy(SCRIPT, tmp_path / SCRIPT.name)
    rep = A.run(root=tmp_path)
    assert {a["name"]: a["count"] for a in rep["antibodies"]} == {a.name: 0 for a in A.ANTIBODIES}
