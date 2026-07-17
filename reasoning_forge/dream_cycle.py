#!/usr/bin/env python3
"""Dream Cycle — nightly cocoon review (Phase 4: self-maintenance).

Reviews the day's reasoning cocoons, flags candidate contradictions,
distills lessons, and writes a dream report. DreamReweaver made
operational: instead of manual archaeology through cocoons/, Codette
reviews her own day on a schedule.

REPORT-ONLY BY DESIGN (standing boundary): this job READS cocoons and
WRITES reports to data/dream_reports/. It never mutates memory stores,
never writes cocoons, never injects anything into recall. Any write-back
of distilled lessons is a separate, human-reviewed step.

Contradiction detection is honest about its limits: it flags CANDIDATE
contradictions (same-topic pairs whose answers diverge by letter, number,
or negation) for review — it does not claim semantic certainty.

Usage:
    python reasoning_forge/dream_cycle.py                # review last 24h
    python reasoning_forge/dream_cycle.py --days 7       # review the week
    python reasoning_forge/dream_cycle.py --days 1 --verbose

Nightly schedule (Windows Task Scheduler):
    schtasks /Create /SC DAILY /ST 03:30 /TN CodetteDreamCycle ^
      /TR "<python> J:\\codette-clean\\reasoning_forge\\dream_cycle.py"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
COCOON_DIR = _REPO / "cocoons"
REPORT_DIR = _REPO / "data" / "dream_reports"

_MCQ_RE = re.compile(r"correct answer is \(([ABCD])\)", re.IGNORECASE)
_NUM_RE = re.compile(r"-?\d+\.?\d*")
_NEG_RE = re.compile(r"\b(no|not|never|isn't|doesn't|cannot|can't|won't|false)\b",
                     re.IGNORECASE)
_STOP = set("the a an is are was were be been being to of in on at for with and or "
            "but if then than so as by from this that these those it its i you he "
            "she we they what which who how why when where do does did can could "
            "would should will your my our their his her them us me".split())


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z']+", (text or "").lower())
            if len(w) > 2 and w not in _STOP}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_recent_cocoons(days: float) -> list[dict]:
    """Load cocoons written in the window that carry a query/response pair."""
    cutoff = time.time() - days * 86400
    out = []
    for f in COCOON_DIR.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        w = d.get("wrapped") or {}
        q, r = w.get("query"), w.get("response")
        if not (isinstance(q, str) and isinstance(r, str) and q.strip() and r.strip()):
            continue
        v3 = d.get("v3") or {}
        out.append({
            "file": f.name,
            "query": q.strip(),
            "response": r.strip(),
            "adapter": w.get("adapter") or v3.get("dominant_perspective") or "?",
            "ts": w.get("timestamp") or d.get("timestamp"),
            "coherence": v3.get("gamma_coherence"),
            "confidence": v3.get("confidence"),
            "hallucination_flag": bool(v3.get("is_hallucination_flagged")),
            "sycophancy_flag": bool(v3.get("is_sycophancy_flagged")),
            "known_contradictions": v3.get("contradicts_cocoon_ids") or [],
        })
    return out


def group_similar(cocoons: list[dict], threshold: float = 0.45) -> list[list[int]]:
    """Group cocoon indices by query similarity (greedy, lexical Jaccard)."""
    words = [_content_words(c["query"]) for c in cocoons]
    groups: list[list[int]] = []
    assigned = [False] * len(cocoons)
    for i in range(len(cocoons)):
        if assigned[i]:
            continue
        group = [i]
        assigned[i] = True
        for j in range(i + 1, len(cocoons)):
            if not assigned[j] and _jaccard(words[i], words[j]) >= threshold:
                group.append(j)
                assigned[j] = True
        groups.append(group)
    return groups


def find_contradiction_candidates(cocoons: list[dict],
                                  groups: list[list[int]]) -> list[dict]:
    """Same-topic pairs whose answers diverge. CANDIDATES, not verdicts."""
    candidates = []
    for group in groups:
        if len(group) < 2:
            continue
        for ai in range(len(group)):
            for bi in range(ai + 1, len(group)):
                a, b = cocoons[group[ai]], cocoons[group[bi]]
                reasons = []
                # MCQ letter divergence
                ma, mb = _MCQ_RE.search(a["response"]), _MCQ_RE.search(b["response"])
                if ma and mb and ma.group(1).upper() != mb.group(1).upper():
                    reasons.append(f"MCQ letters differ: {ma.group(1)} vs {mb.group(1)}")
                # negation asymmetry on similar-length short answers
                na = bool(_NEG_RE.search(a["response"][:200]))
                nb = bool(_NEG_RE.search(b["response"][:200]))
                if na != nb and _jaccard(_content_words(a["response"]),
                                         _content_words(b["response"])) > 0.3:
                    reasons.append("negation asymmetry in similar responses")
                # leading numeric answer divergence
                fa, fb = _NUM_RE.findall(a["response"][:120]), _NUM_RE.findall(b["response"][:120])
                if fa and fb and fa[0] != fb[0] and _jaccard(
                        _content_words(a["query"]), _content_words(b["query"])) > 0.6:
                    reasons.append(f"leading numbers differ: {fa[0]} vs {fb[0]}")
                if reasons:
                    candidates.append({
                        "a": a["file"], "b": b["file"],
                        "query_a": a["query"][:140], "query_b": b["query"][:140],
                        "reasons": reasons,
                    })
    return candidates


def distill(cocoons: list[dict], groups: list[list[int]],
            contradictions: list[dict]) -> dict:
    themes = Counter()
    for c in cocoons:
        themes.update(_content_words(c["query"]))
    adapters = Counter(c["adapter"] for c in cocoons)
    low_coherence = [c for c in cocoons
                     if isinstance(c["coherence"], (int, float)) and c["coherence"] < 0.5]
    flagged = [c for c in cocoons if c["hallucination_flag"] or c["sycophancy_flag"]]
    known = [c for c in cocoons if c["known_contradictions"]]

    lessons = []
    if contradictions:
        lessons.append(f"{len(contradictions)} candidate contradiction(s) need review "
                       "— same-topic answers diverged.")
    if low_coherence:
        lessons.append(f"{len(low_coherence)} turn(s) ran at coherence < 0.5 — "
                       "inspect what those queries had in common.")
    if flagged:
        lessons.append(f"{len(flagged)} turn(s) carried hallucination/sycophancy flags.")
    big = [g for g in groups if len(g) >= 3]
    if big:
        top = max(big, key=len)
        rep = cocoons[top[0]]["query"][:100]
        lessons.append(f"Most-revisited topic ({len(top)} turns): \"{rep}\" — "
                       "recurring themes are candidates for memory distillation.")
    if not lessons:
        lessons.append("Quiet day: no contradictions, flags, or low-coherence turns.")

    return {
        "top_themes": themes.most_common(12),
        "adapter_usage": adapters.most_common(),
        "low_coherence_count": len(low_coherence),
        "flagged_count": len(flagged),
        "already_marked_contradictions": len(known),
        "lessons": lessons,
    }


def write_report(cocoons, groups, contradictions, summary) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    md = REPORT_DIR / f"dream_{stamp}.md"
    js = REPORT_DIR / f"dream_{stamp}.json"

    lines = [f"# Dream Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             "",
             f"Reviewed **{len(cocoons)}** cocoons in **{len(groups)}** topic groups.",
             "",
             "## Lessons"]
    lines += [f"- {l}" for l in summary["lessons"]]
    lines += ["", "## Candidate contradictions (need human review)"]
    if contradictions:
        for c in contradictions[:20]:
            lines += [f"- `{c['a']}` vs `{c['b']}` — {'; '.join(c['reasons'])}",
                      f"  - A: {c['query_a']}", f"  - B: {c['query_b']}"]
    else:
        lines.append("- none found")
    lines += ["", "## Day shape",
              f"- Adapter usage: {dict(summary['adapter_usage'])}",
              f"- Top themes: {', '.join(w for w, _ in summary['top_themes'])}",
              f"- Low-coherence turns: {summary['low_coherence_count']}",
              f"- Flagged turns: {summary['flagged_count']}",
              "",
              "_Report-only job: no memory was modified. Write-back of lessons is a "
              "separate human-reviewed step._"]
    md.write_text("\n".join(lines), encoding="utf-8")
    js.write_text(json.dumps({
        "generated": datetime.now().isoformat(),
        "cocoons_reviewed": len(cocoons), "groups": len(groups),
        "contradiction_candidates": contradictions, "summary": summary,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=1.0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cocoons = load_recent_cocoons(args.days)
    print(f"Dream cycle: {len(cocoons)} reasoning cocoons from the last {args.days} day(s)")
    if not cocoons:
        print("Nothing to review — no report written.")
        return

    groups = group_similar(cocoons)
    contradictions = find_contradiction_candidates(cocoons, groups)
    summary = distill(cocoons, groups, contradictions)
    report = write_report(cocoons, groups, contradictions, summary)

    for lesson in summary["lessons"]:
        print(f"  - {lesson}")
    print(f"\nReport: {report}")


if __name__ == "__main__":
    main()
