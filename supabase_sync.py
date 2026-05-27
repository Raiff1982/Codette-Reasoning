"""
supabase_sync.py — Codette ↔ Supabase real-time sync
======================================================

Three sync surfaces:

1. Cocoons      → public.cocoons           (upsert on every forge write)
2. Benchmark    → benchmark_runs +         (push after codette_benchmark_suite.py)
                  benchmark_tests +
                  benchmark_stats
3. Runtime      → benchmark_results        (push after runtime benchmark)

Credentials are loaded from .env (SUPABASE_URL + SUPABASE_KEY).
All operations are best-effort — exceptions are logged but never propagate
to the caller so a Supabase outage never breaks local inference.

Usage:
    from supabase_sync import get_client, sync_cocoon, push_benchmark_run

Original: Jonathan Harrison (Raiff1982/Codette-Reasoning)
"""

from __future__ import annotations

import logging
import math
import os
import uuid
from typing import Any, Dict, List, Optional


def _safe_float(val, default: float = 0.0) -> float:
    """Return a JSON-safe float — replaces inf / -inf / nan with default."""
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _sanitize_dict(obj: Any) -> Any:
    """Recursively replace non-finite floats in dicts/lists so JSON serialises cleanly."""
    if isinstance(obj, dict):
        return {k: _sanitize_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_dict(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else 0.0
    return obj

logger = logging.getLogger(__name__)

# ── Credential loading ────────────────────────────────────────────────────────

def _load_env() -> tuple[str, str]:
    """Return (url, key) from env vars or .env file.

    Searches several candidate paths so the module works whether it is
    imported from the project root, from inference/, or from any subdir.
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        try:
            from dotenv import load_dotenv
            _here = os.path.dirname(os.path.abspath(__file__))
            _candidates = [
                os.path.join(_here, ".env"),                  # same dir as this file
                os.path.join(_here, "..", ".env"),            # one level up (project root)
                os.path.join(_here, "..", "..", ".env"),      # two levels up
                os.path.join(os.getcwd(), ".env"),            # working directory
            ]
            for _candidate in _candidates:
                _candidate = os.path.normpath(_candidate)
                if os.path.isfile(_candidate):
                    load_dotenv(_candidate, override=False)
                    logger.debug(f"[supabase_sync] loaded .env from {_candidate}")
                    break
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")
        except Exception as e:
            logger.debug(f"[supabase_sync] dotenv load failed: {e}")
    return url, key


# ── Singleton client ──────────────────────────────────────────────────────────

_client = None

def get_client():
    """Return a cached Supabase client, or None if credentials are missing."""
    global _client
    if _client is not None:
        return _client
    url, key = _load_env()
    if not url or not key:
        logger.warning("[supabase_sync] Missing SUPABASE_URL / SUPABASE_KEY — sync disabled")
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info(f"[supabase_sync] Connected to {url}")
    except Exception as e:
        logger.warning(f"[supabase_sync] Could not create client: {e}")
        return None
    return _client


# ── Cocoon sync ───────────────────────────────────────────────────────────────

def sync_cocoon(cocoon: Dict[str, Any]) -> bool:
    """
    Upsert a CocoonV3 dict to public.cocoons.

    Maps the local CocoonV3 fields to the Supabase schema.
    Returns True on success, False on any error.
    """
    client = get_client()
    if not client:
        return False
    try:
        # Map CocoonV3 → Supabase cocoons schema
        row = {
            "source_id":   str(cocoon.get("cocoon_id") or cocoon.get("id") or ""),
            "title":       str(cocoon.get("query", ""))[:500],
            "summary":     str(cocoon.get("response", ""))[:2000],
            "quote":       str(cocoon.get("synthesis", "") or cocoon.get("response", ""))[:1000],
            "emotion":     str(cocoon.get("dominant_emotion", "") or cocoon.get("emotional_state", "")),
            "cocoon_type": str(cocoon.get("cocoon_type", "forge")),
            "tags":        cocoon.get("tags") or [],
            "intensity":   float(cocoon.get("cocoon_integrity_score") or cocoon.get("intensity") or 0.5),
            "metadata": {
                "adapter":          cocoon.get("adapter"),
                "epsilon":          cocoon.get("epsilon"),
                "gamma":            cocoon.get("gamma"),
                "integrity_score":  cocoon.get("cocoon_integrity_score"),
                "version":          cocoon.get("version", "v3"),
            },
            "raw": {k: v for k, v in cocoon.items()
                    if k not in ("query", "response", "synthesis")},
        }
        # Use None for missing source_id — Postgres allows multiple NULLs in unique columns
        if not row["source_id"]:
            row["source_id"] = None

        client.table("cocoons").upsert(row, on_conflict="source_id").execute()
        return True
    except Exception as e:
        logger.debug(f"[supabase_sync] sync_cocoon failed: {e}")
        return False


# ── Publishable benchmark push ────────────────────────────────────────────────

def push_benchmark_run(
    condition_stats: List[Dict],
    comparisons: List[Dict],
    scores_by_problem: List[Dict],
    source_file: str = "",
) -> Optional[str]:
    """
    Push a full publishable benchmark run to Supabase.

    Args:
        condition_stats: list of {condition, n, mean_composite, std_composite,
                                   dimension_means: {dim: float}}
        comparisons:    list of {label, condition_a, condition_b, mean_a, mean_b,
                                  delta, delta_pct, cohens_d, t_stat, p_value}
        scores_by_problem: list of {problem_id, condition, composite,
                                     dimensions: {dim: float}, response_text,
                                     response_length, latency_ms}
        source_file:    path of the report file for traceability

    Returns:
        run_id (uuid str) on success, None on failure.
    """
    client = get_client()
    if not client:
        return None
    try:
        import datetime
        codette_row = next((s for s in condition_stats if s["condition"] == "CODETTE"), None)
        overall_score = codette_row["mean_composite"] if codette_row else None
        category_scores = {
            s["condition"]: {
                "composite": s["mean_composite"],
                "std":       s["std_composite"],
                **s.get("dimension_means", {}),
            }
            for s in condition_stats
        }

        # Insert run
        run_ts = datetime.datetime.utcnow().isoformat() + "Z"
        run_resp = (
            client.table("benchmark_runs")
            .insert({
                "run_timestamp":  run_ts,
                "model":          "codette-llama-3.1-8b",
                "backend":        "llama.cpp",
                "overall_score":  overall_score,
                "total_tests":    len(scores_by_problem),
                "category_scores": category_scores,
                "source_file":    source_file,
            })
            .execute()
        )
        run_id = run_resp.data[0]["id"]

        # Insert per-problem scores as benchmark_tests rows
        test_rows = []
        for s in scores_by_problem:
            test_rows.append({
                "run_id":        run_id,
                "query":         s.get("problem_id", ""),
                "category":      s.get("problem_id", "").split("_")[0] if "_" in s.get("problem_id","") else "",
                "score":         s.get("composite"),
                "passed":        (s.get("composite") or 0) >= 0.65,
                "response_text": (s.get("response_text") or "")[:2000],
                "latency_ms":    s.get("latency_ms"),
                "tier":          s.get("condition"),
                "metadata":      {d: v for d, v in (s.get("dimensions") or {}).items()},
            })
        if test_rows:
            client.table("benchmark_tests").insert(test_rows).execute()

        # Insert statistical comparisons
        stat_rows = []
        for c in comparisons:
            stat_rows.append({
                "label":       c.get("comparison") or c.get("label", ""),
                "condition_a": c.get("condition_a", ""),
                "condition_b": c.get("condition_b", ""),
                "mean_a":      c.get("mean_a"),
                "mean_b":      c.get("mean_b"),
                "mean_diff":   c.get("delta"),
                "t_statistic": c.get("t_stat"),
                "p_value":     c.get("p_value"),
                "cohens_d":    c.get("cohens_d"),
                "source_file": source_file,
            })
        if stat_rows:
            client.table("benchmark_stats").insert(stat_rows).execute()

        logger.info(f"[supabase_sync] Benchmark run {run_id} pushed ({len(test_rows)} tests)")
        return run_id

    except Exception as e:
        logger.warning(f"[supabase_sync] push_benchmark_run failed: {e}")
        return None


# ── Runtime benchmark push ────────────────────────────────────────────────────

def push_runtime_result(
    case_id: str,
    category: str,
    score: float,
    passed: bool,
    latency_ms: float,
    checks: Dict[str, Any],
    response_text: str = "",
) -> bool:
    """Push a single runtime benchmark case result to benchmark_results."""
    client = get_client()
    if not client:
        return False
    try:
        client.table("benchmark_results").insert({
            "test_type":              category,
            "query":                  case_id,
            "codette_score":          score,
            "improvement":            score,
            "processing_time":        latency_ms / 1000.0,
            "statistical_significance": 1.0 if passed else 0.0,
            "test_conditions":        str(checks),
            "competitor_scores":      {},
        }).execute()
        return True
    except Exception as e:
        logger.debug(f"[supabase_sync] push_runtime_result failed: {e}")
        return False


# ── Bulk cocoon backfill ──────────────────────────────────────────────────────

def bulk_sync_cocoons(
    cocoons: List[Dict],
    batch_size: int = 50,
    progress_cb=None,
) -> Dict[str, int]:
    """
    Upsert a list of cocoon dicts to Supabase in batches.

    Args:
        cocoons      : List of cocoon dicts from UnifiedMemory
        batch_size   : How many to upsert per API call (Supabase limit ~500)
        progress_cb  : Optional callable(done, total) for progress reporting

    Returns:
        {"synced": int, "skipped": int, "errors": int}
    """
    client = get_client()
    if not client:
        logger.warning("[supabase_sync] bulk_sync_cocoons: no client")
        return {"synced": 0, "skipped": 0, "errors": len(cocoons)}

    synced = skipped = errors = 0
    total = len(cocoons)

    # Build rows — same mapping as sync_cocoon() but batched
    rows = []
    for c in cocoons:
        try:
            source_id = str(c.get("cocoon_id") or c.get("id") or "")
            row = {
                "title":       str(c.get("query", ""))[:500],
                "summary":     str(c.get("response", ""))[:2000],
                "quote":       str(c.get("synthesis", "") or c.get("response", ""))[:1000],
                "emotion":     str(c.get("emotion") or c.get("dominant_emotion") or c.get("emotional_state", "")),
                "cocoon_type": str(c.get("cocoon_type", "memory")),
                "tags":        c.get("tags") or [],
                "intensity":   _safe_float(c.get("cocoon_integrity_score") or c.get("intensity") or c.get("importance", 5) / 10),
                "metadata": {
                    "adapter":         c.get("adapter"),
                    "domain":          c.get("domain"),
                    "complexity":      c.get("complexity"),
                    "importance":      c.get("importance"),
                    "timestamp":       c.get("timestamp"),
                    "version":         c.get("version", "v3"),
                },
                "raw": {k: v for k, v in c.items()
                        if k not in ("query", "response", "synthesis")},
            }
            if source_id:
                row["source_id"] = source_id
            # Leave source_id absent (NULL) for rows without one —
            # Postgres allows multiple NULLs in a unique column
            rows.append(_sanitize_dict(row))
        except Exception as e:
            logger.debug(f"[supabase_sync] row build failed: {e}")
            errors += 1

    # Upsert in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            client.table("cocoons").upsert(batch, on_conflict="source_id").execute()
            synced += len(batch)
        except Exception as e:
            logger.warning(f"[supabase_sync] batch {i//batch_size + 1} failed: {e}")
            errors += len(batch)
        if progress_cb:
            progress_cb(min(i + batch_size, len(rows)), total)

    logger.info(f"[supabase_sync] bulk sync complete: {synced} synced, {skipped} skipped, {errors} errors")
    return {"synced": synced, "skipped": skipped, "errors": errors}


# ── Quick connectivity test ───────────────────────────────────────────────────

def ping() -> bool:
    """Return True if Supabase is reachable and credentials work."""
    client = get_client()
    if not client:
        return False
    try:
        client.table("cocoons").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.warning(f"[supabase_sync] ping failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Supabase sync utilities")
    parser.add_argument("--ping",       action="store_true", help="Test connectivity")
    parser.add_argument("--sync-all",   action="store_true", help="Bulk sync all local cocoons")
    parser.add_argument("--batch-size", type=int, default=50, help="Upsert batch size (default 50)")
    args = parser.parse_args()

    if args.ping or not any([args.sync_all]):
        ok = ping()
        print(f"Supabase ping: {'OK' if ok else 'FAILED'}")

    if args.sync_all:
        print("Loading local cocoons from UnifiedMemory...")
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(__file__))
            from reasoning_forge.unified_memory import UnifiedMemory
            mem = UnifiedMemory()
            total = mem._total_stored
            print(f"Found {total} cocoons locally — starting bulk sync...")

            # Pull all cocoons via recent recall in large batches
            all_cocoons = mem.recall_recent(limit=total)
            print(f"Loaded {len(all_cocoons)} cocoons")

            def _progress(done, total):
                pct = done / max(total, 1) * 100
                print(f"  {done}/{total} ({pct:.0f}%)", end="\r", flush=True)

            result = bulk_sync_cocoons(all_cocoons, batch_size=args.batch_size, progress_cb=_progress)
            print()
            print(f"Done — synced: {result['synced']}, errors: {result['errors']}")
        except Exception as e:
            print(f"Sync failed: {e}")
