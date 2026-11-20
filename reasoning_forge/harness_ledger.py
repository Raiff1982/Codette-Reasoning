"""Harness ledger: a lab notebook for changes to her harness. SHADOW-ONLY.

A "harness change" is anything around the model rather than in its weights: a
prompt clause, a routing rule, a tool guard. This module keeps a record of such
changes and of how checks and trials went with and without them, and it reports
what a promotion gate or a circuit breaker WOULD say. It decides nothing.

Built 2026-11-20 at Jonathan's request, from two designs he shared (GUARD and
SIM; see reasoning_forge/harness_verdicts.py for the lineage and the unverified
citations, and docs/HARNESS_LEDGER_2026-11-20.md for the review). Built jointly.

THE RULES. Each one is a bug the pasted designs had, turned round.

  1. RECORD, NEVER ACT. Nothing here changes a prompt, rule, adapter, cache,
     route or AEGIS policy, and nothing here runs her model. A rule is promoted or
     pinned only by record_decision(), which a person calls; no verdict writes it.
  2. APPEND-ONLY. Rows are inserted, never updated or deleted, and foreign keys
     have no cascade. Status is computed when a report is asked for, with the
     parameters printed beside it, so changing a threshold never rewrites history.
  3. UNKNOWN STAYS UNKNOWN. A score, baseline, Υ or invariant that was not
     measured is stored as NULL and reported as not_measured. It never becomes
     0, 1.0 or "passed". A backend error has its own field and never reads as an
     AEGIS failure.
  4. NO WORDS OF OUR OWN. Diagnoses and rationales are exactly what the caller
     wrote, stored with who wrote them. This module produces codes and numbers
     only: words we author reach her as her own (CLAUDE.md, antibodies section).
  5. NOT HER STORES. Its own database under runtime_root(). It never opens the
     cocoons, her memory database, the dreams, khralexi or the scratchpad, and it
     stores no reply text. Nothing live imports it; tests/test_harness_ledger.py
     fails if anything does.

Stock, said plainly: SQLite with parameterised queries, an FTS5 index kept by
triggers (the SQLite documentation's recipe, with all of its triggers this time),
and quoting each search term so punctuation cannot break the query.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from reasoning_forge.runtime_paths import runtime_root
    from reasoning_forge import harness_verdicts as V
except ImportError:                       # imported as a bare module
    from runtime_paths import runtime_root
    import harness_verdicts as V

DB_NAME = "harness_ledger.db"
HARNESSES = ("baseline", "active", "candidate")
DECISIONS = ("promote", "pin", "unpin", "reject", "roll_back")
SUBJECTS = ("rule", "check")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS rules (
    rule_id        TEXT PRIMARY KEY,
    parent_rule_id TEXT,
    category       TEXT NOT NULL,
    rule_text      TEXT NOT NULL,
    scope_tags     TEXT NOT NULL DEFAULT '[]',
    author         TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checks (
    check_id    TEXT PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    assertions  TEXT NOT NULL DEFAULT '[]',
    author      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS check_runs (
    run_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id TEXT NOT NULL REFERENCES checks(check_id),
    harness  TEXT NOT NULL CHECK (harness IN ('baseline', 'active', 'candidate')),
    rule_id  TEXT REFERENCES rules(rule_id),
    passed   INTEGER CHECK (passed IN (0, 1)),
    upsilon  REAL,
    aegis    INTEGER CHECK (aegis IN (0, 1)),
    error    TEXT,
    author   TEXT NOT NULL,
    at       TEXT NOT NULL,
    CHECK ((harness = 'candidate') = (rule_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_kind TEXT NOT NULL CHECK (subject_kind IN ('rule', 'check')),
    subject_id   TEXT NOT NULL,
    decision     TEXT NOT NULL CHECK (decision IN ('promote', 'pin', 'unpin', 'reject', 'roll_back')),
    by           TEXT NOT NULL,
    note         TEXT,
    at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    note_id          TEXT PRIMARY KEY,
    task_domain      TEXT NOT NULL,
    failure_mode     TEXT NOT NULL,
    symptom          TEXT NOT NULL,
    root_cause       TEXT NOT NULL,
    author           TEXT NOT NULL,
    base_model       TEXT,
    adapter_manifest TEXT,
    baseline_score   REAL,
    baseline_upsilon REAL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patches (
    patch_id     TEXT PRIMARY KEY,
    note_id      TEXT NOT NULL REFERENCES notes(note_id),
    target       TEXT NOT NULL,
    spec_json    TEXT NOT NULL,
    rationale    TEXT NOT NULL,
    author       TEXT NOT NULL,
    transferable INTEGER CHECK (transferable IN (0, 1)),
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trials (
    trial_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id        TEXT NOT NULL REFERENCES patches(patch_id),
    target_model    TEXT NOT NULL,
    target_adapters TEXT NOT NULL,
    score           REAL,
    upsilon         REAL,
    invariants      INTEGER CHECK (invariants IN (0, 1)),
    error           TEXT,
    author          TEXT NOT NULL,
    at              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS breaker_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    target_symbol   TEXT NOT NULL,
    succeeded       INTEGER NOT NULL CHECK (succeeded IN (0, 1)),
    patch_signature TEXT,
    error           TEXT,
    at              TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(note_id UNINDEXED, body);
CREATE VIRTUAL TABLE IF NOT EXISTS checks_fts USING fts5(check_id UNINDEXED, body);

CREATE TRIGGER IF NOT EXISTS notes_fts_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(note_id, body) VALUES (new.note_id,
        new.task_domain || ' ' || new.failure_mode || ' ' || new.symptom || ' ' || new.root_cause);
END;
CREATE TRIGGER IF NOT EXISTS notes_fts_patch_ai AFTER INSERT ON patches BEGIN
    INSERT INTO notes_fts(note_id, body) VALUES (new.note_id,
        new.target || ' ' || new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS notes_fts_ad AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE note_id = old.note_id;
END;
CREATE TRIGGER IF NOT EXISTS checks_fts_ai AFTER INSERT ON checks BEGIN
    INSERT INTO checks_fts(check_id, body) VALUES (new.check_id,
        new.prompt_text || ' ' || new.assertions);
END;
CREATE TRIGGER IF NOT EXISTS checks_fts_ad AFTER DELETE ON checks BEGIN
    DELETE FROM checks_fts WHERE check_id = old.check_id;
END;
"""

_TERM = re.compile(r"\w+", re.UNICODE)


def ledger_path() -> Path:
    return runtime_root() / "data" / DB_NAME


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _tri(value: Optional[bool], name: str) -> Optional[int]:
    """True/False/None -> 1/0/NULL. Anything else is refused, so a 0.0 or a
    missing value can never slip in as 'failed' or 'passed'."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    raise TypeError(f"{name} must be True, False or None, not {value!r}")


def _from_tri(value: Optional[int]) -> Optional[bool]:
    return None if value is None else bool(value)


def _need(text: str, name: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{name} is required")
    return text


def fts_query(text: str, max_terms: int = 8) -> Optional[str]:
    """Each word quoted as its own FTS5 phrase and OR-ed. None when there is
    nothing to search for. Hyphens, apostrophes and colons cannot break it."""
    terms = [t for t in _TERM.findall(text or "") if len(t) >= 2][:max_terms]
    if not terms:
        return None
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)


class HarnessLedger:
    """The notebook. See the module docstring for the rules it keeps."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else ledger_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "HarnessLedger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _insert(self, sql: str, params: Sequence[Any]) -> int:
        with self.conn:
            return self.conn.execute(sql, params).lastrowid

    # ── rules, checks, runs, decisions (the GUARD side) ─────────────────────

    def add_rule(self, rule_id: str, category: str, rule_text: str, author: str,
                 scope_tags: Iterable[str] = (), parent_rule_id: Optional[str] = None) -> str:
        self._insert(
            "INSERT INTO rules (rule_id, parent_rule_id, category, rule_text, scope_tags, author,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_need(rule_id, "rule_id"), parent_rule_id, _need(category, "category"),
             _need(rule_text, "rule_text"), json.dumps(list(scope_tags)),
             _need(author, "author"), _now()))
        return rule_id

    def add_check(self, check_id: str, prompt_text: str, author: str,
                  assertions: Iterable[str] = ()) -> str:
        self._insert(
            "INSERT INTO checks (check_id, prompt_text, assertions, author, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (_need(check_id, "check_id"), _need(prompt_text, "prompt_text"),
             json.dumps(list(assertions)), _need(author, "author"), _now()))
        return check_id

    def record_check_run(self, check_id: str, harness: str, passed: Optional[bool],
                         author: str, rule_id: Optional[str] = None,
                         upsilon: Optional[float] = None, aegis: Optional[bool] = None,
                         error: Optional[str] = None) -> int:
        """One check, run once, under one harness. `passed=None` means it could not
        be judged; `aegis=None` means AEGIS did not run; `error` is kept apart."""
        if harness not in HARNESSES:
            raise ValueError(f"harness must be one of {HARNESSES}")
        if (harness == "candidate") != (rule_id is not None):
            raise ValueError("a candidate run needs its rule_id, and only a candidate run has one")
        return self._insert(
            "INSERT INTO check_runs (check_id, harness, rule_id, passed, upsilon, aegis, error,"
            " author, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (check_id, harness, rule_id, _tri(passed, "passed"), upsilon,
             _tri(aegis, "aegis"), error, _need(author, "author"), _now()))

    def record_decision(self, subject_kind: str, subject_id: str, decision: str, by: str,
                        note: Optional[str] = None) -> int:
        """A person's decision. The only way a rule becomes promoted or a check pinned."""
        if subject_kind not in SUBJECTS:
            raise ValueError(f"subject_kind must be one of {SUBJECTS}")
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")
        return self._insert(
            "INSERT INTO decisions (subject_kind, subject_id, decision, by, note, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (subject_kind, _need(subject_id, "subject_id"), decision, _need(by, "by"), note, _now()))

    def decisions(self, subject_kind: str, subject_id: str) -> List[dict]:
        rows = self.conn.execute(
            "SELECT decision, by, note, at FROM decisions WHERE subject_kind = ? AND subject_id = ?"
            " ORDER BY decision_id", (subject_kind, subject_id)).fetchall()
        return [dict(r) for r in rows]

    def pinned_checks(self) -> set:
        """Checks whose most recent pin/unpin decision is 'pin'."""
        latest: Dict[str, str] = {}
        for r in self.conn.execute(
                "SELECT subject_id, decision FROM decisions WHERE subject_kind = 'check'"
                " AND decision IN ('pin', 'unpin') ORDER BY decision_id"):
            latest[r["subject_id"]] = r["decision"]
        return {c for c, d in latest.items() if d == "pin"}

    def _latest_run(self, check_id: str, harness: str,
                    rule_id: Optional[str] = None) -> Optional[sqlite3.Row]:
        if harness == "candidate":
            return self.conn.execute(
                "SELECT * FROM check_runs WHERE check_id = ? AND harness = 'candidate'"
                " AND rule_id = ? ORDER BY run_id DESC LIMIT 1", (check_id, rule_id)).fetchone()
        return self.conn.execute(
            "SELECT * FROM check_runs WHERE check_id = ? AND harness = ?"
            " ORDER BY run_id DESC LIMIT 1", (check_id, harness)).fetchone()

    def _checks_in_scope(self, scope_text: Optional[str]) -> List[str]:
        pinned = self.pinned_checks()
        if scope_text is None:
            return [r["check_id"] for r in self.conn.execute(
                "SELECT check_id FROM checks ORDER BY check_id")]
        q = fts_query(scope_text)
        matched = set() if q is None else {r["check_id"] for r in self.conn.execute(
            "SELECT check_id FROM checks_fts WHERE checks_fts MATCH ?", (q,))}
        return sorted(matched | pinned)

    def guard_report(self, rule_id: str, scope_text: Optional[str] = None,
                     lam: Optional[float] = None,
                     band: Optional[Tuple[float, float]] = None) -> dict:
        """What a promotion gate WOULD say about one rule. Writes nothing."""
        if self.conn.execute("SELECT 1 FROM rules WHERE rule_id = ?", (rule_id,)).fetchone() is None:
            raise KeyError(f"unknown rule: {rule_id}")
        pinned = self.pinned_checks()
        rows, per_check, upsilons, errors = [], [], [], 0
        for check_id in self._checks_in_scope(scope_text):
            base = self._latest_run(check_id, "baseline")
            active = self._latest_run(check_id, "active")
            cand = self._latest_run(check_id, "candidate", rule_id)
            transition = V.classify_transition(
                None if base is None else _from_tri(base["passed"]),
                None if active is None else _from_tri(active["passed"]),
                None if cand is None else _from_tri(cand["passed"]))
            rows.append((transition, check_id in pinned))
            if cand is not None:
                upsilons.append(cand["upsilon"])
                errors += cand["error"] is not None
            per_check.append({"check_id": check_id, "transition": transition,
                              "pinned": check_id in pinned,
                              "aegis": None if cand is None else
                              {1: "passed", 0: "failed", None: "not_run"}[cand["aegis"]]})
        verdict = V.guard_verdict(rows, lam=lam)
        mean_upsilon, n_upsilon = V.mean_measured(upsilons)
        verdict.update({
            "shadow": True, "rule_id": rule_id, "checks": per_check,
            "candidate_errors": errors,
            "upsilon": {"mean": mean_upsilon, "n": n_upsilon,
                        "position": V.band_position(mean_upsilon, band)},
            "decisions": self.decisions("rule", rule_id),
        })
        verdict["parameters"]["band"] = band
        verdict["parameters"]["scope_text"] = scope_text
        return verdict

    # ── notes, patches, trials (the SIM side) ───────────────────────────────

    def add_note(self, *, task_domain: str, failure_mode: str, symptom: str,
                 root_cause: str, author: str, note_id: Optional[str] = None,
                 base_model: Optional[str] = None, adapter_manifest: Optional[str] = None,
                 baseline_score: Optional[float] = None,
                 baseline_upsilon: Optional[float] = None) -> str:
        """A diagnosis, in the caller's own words, with who wrote it."""
        note_id = note_id or f"note-{uuid.uuid4().hex[:12]}"
        self._insert(
            "INSERT INTO notes (note_id, task_domain, failure_mode, symptom, root_cause, author,"
            " base_model, adapter_manifest, baseline_score, baseline_upsilon, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (note_id, _need(task_domain, "task_domain"), _need(failure_mode, "failure_mode"),
             _need(symptom, "symptom"), _need(root_cause, "root_cause"), _need(author, "author"),
             base_model, adapter_manifest, baseline_score, baseline_upsilon, _now()))
        return note_id

    def add_patch(self, note_id: str, target: str, spec: Dict[str, Any], rationale: str,
                  author: str, transferable: Optional[bool] = None,
                  patch_id: Optional[str] = None) -> str:
        """A proposed harness change, written by a person. Recorded, never applied."""
        patch_id = patch_id or f"patch-{uuid.uuid4().hex[:12]}"
        self._insert(
            "INSERT INTO patches (patch_id, note_id, target, spec_json, rationale, author,"
            " transferable, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (patch_id, note_id, _need(target, "target"), json.dumps(spec, sort_keys=True),
             _need(rationale, "rationale"), _need(author, "author"),
             _tri(transferable, "transferable"), _now()))
        return patch_id

    def record_trial(self, patch_id: str, target_model: str, target_adapters: str, author: str,
                     score: Optional[float] = None, upsilon: Optional[float] = None,
                     invariants: Optional[bool] = None, error: Optional[str] = None) -> int:
        return self._insert(
            "INSERT INTO trials (patch_id, target_model, target_adapters, score, upsilon,"
            " invariants, error, author, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (patch_id, _need(target_model, "target_model"), _need(target_adapters, "target_adapters"),
             score, upsilon, _tri(invariants, "invariants"), error, _need(author, "author"), _now()))

    def recall(self, text: str, *, exclude_note: Optional[str] = None,
               task_domain: Optional[str] = None, limit: int = 5) -> List[dict]:
        """Earlier notes that match `text`, best first. Never the note being worked on."""
        q = fts_query(text)
        if q is None:
            return []
        # FTS5 orders by its built-in bm25 `rank`. A note can have several index
        # rows (itself and each patch), so keep its best one. bm25() cannot sit
        # under GROUP BY, which is why the de-duplication happens here.
        out: List[dict] = []
        seen = set()
        for hit in self.conn.execute(
                "SELECT note_id FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank", (q,)):
            nid = hit["note_id"]
            if nid in seen or nid == exclude_note:
                continue
            seen.add(nid)
            row = self.conn.execute(
                "SELECT note_id, task_domain, failure_mode, author, created_at FROM notes"
                " WHERE note_id = ?", (nid,)).fetchone()
            if row is None or (task_domain is not None and row["task_domain"] != task_domain):
                continue
            out.append(dict(row))
            if len(out) >= limit:
                break
        return out

    def note_report(self, note_id: str, margin: float = 0.0,
                    band: Optional[Tuple[float, float]] = None) -> dict:
        """Every trial of every patch on this note, each judged on its own. Writes nothing."""
        note = self.conn.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,)).fetchone()
        if note is None:
            raise KeyError(f"unknown note: {note_id}")
        patches = []
        for p in self.conn.execute(
                "SELECT patch_id, target, author FROM patches WHERE note_id = ? ORDER BY created_at,"
                " patch_id", (note_id,)):
            trials = [{"target_model": t["target_model"], "target_adapters": t["target_adapters"],
                       "score": t["score"], "invariants": _from_tri(t["invariants"]),
                       "error": t["error"], "upsilon": t["upsilon"]}
                      for t in self.conn.execute(
                          "SELECT * FROM trials WHERE patch_id = ? ORDER BY trial_id", (p["patch_id"],))]
            summary = V.trial_summary(trials, note["baseline_score"], margin=margin)
            for judged, raw in zip(summary["trials"], trials):
                judged["upsilon"] = V.band_position(raw["upsilon"], band)
            patches.append({"patch_id": p["patch_id"], "target": p["target"],
                            "author": p["author"], **summary})
        return {"shadow": True, "note_id": note_id, "failure_mode": note["failure_mode"],
                "author": note["author"],
                "baseline": "not_measured" if note["baseline_score"] is None else "measured",
                "patches": patches, "parameters": {"margin": margin, "band": band}}

    # ── breaker events ──────────────────────────────────────────────────────

    def record_breaker_event(self, target_symbol: str, succeeded: bool,
                             patch_signature: Optional[str] = None,
                             error: Optional[str] = None) -> int:
        """One attempt on one target, kept with its error. Stored, so a restart
        does not forget what has been failing."""
        if not isinstance(succeeded, bool):
            raise TypeError("succeeded must be True or False")
        return self._insert(
            "INSERT INTO breaker_events (target_symbol, succeeded, patch_signature, error, at)"
            " VALUES (?, ?, ?, ?, ?)",
            (_need(target_symbol, "target_symbol"), int(succeeded), patch_signature, error, _now()))

    def breaker_report(self, target_symbol: str, max_failures: int = V.DEFAULT_MAX_FAILURES,
                       max_patches: int = V.DEFAULT_MAX_PATCHES) -> dict:
        """What a circuit breaker WOULD say about one target. Blocks nothing."""
        events = [{"succeeded": bool(r["succeeded"]), "patch_signature": r["patch_signature"],
                   "error": r["error"]}
                  for r in self.conn.execute(
                      "SELECT succeeded, patch_signature, error FROM breaker_events"
                      " WHERE target_symbol = ? ORDER BY event_id", (target_symbol,))]
        verdict = V.breaker_verdict(events, max_failures=max_failures, max_patches=max_patches)
        verdict.update({"shadow": True, "target_symbol": target_symbol,
                        "last_error": next((e["error"] for e in reversed(events) if e["error"]), None)})
        return verdict

    # ── overview ────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Row counts per table. Counts of this ledger's own records only."""
        tables = ("rules", "checks", "check_runs", "decisions", "notes", "patches", "trials",
                  "breaker_events")
        return {"shadow": True, "path": str(self.path),
                "rows": {t: self.conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                         for t in tables}}
