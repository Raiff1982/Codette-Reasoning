"""
Dataset Validator - checks JSONL training dataset quality.

Validates format, structure, duplicates, length, diversity,
and can auto-filter to produce a clean dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_hash(text: str) -> str:
    """SHA-256 of normalised text for exact duplicate detection."""
    normalised = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _word_set(text: str) -> Set[str]:
    """Set of lowercase words for Jaccard similarity."""
    return set(re.findall(r"[a-z]{2,}", text.lower()))


def _jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _extract_topic_words(text: str, top_n: int = 5) -> List[str]:
    """Extract dominant topic words from text."""
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "and", "but", "or", "if", "that", "this", "what",
        "which", "it", "its", "they", "them", "their", "not", "you",
        "your", "can", "could", "should", "may", "might", "must",
        "how", "why", "when", "where", "who", "whom", "about",
    }
    words = re.findall(r"[a-z]{3,}", text.lower())
    filtered = [w for w in words if w not in stop]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]


# ---------------------------------------------------------------------------
# Validation Issue
# ---------------------------------------------------------------------------

class ValidationIssue:
    """Represents a single validation problem."""

    def __init__(self, line_num: int, severity: str, code: str, message: str):
        self.line_num = line_num
        self.severity = severity  # "error", "warning", "info"
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] Line {self.line_num}: {self.code} - {self.message}"


# ---------------------------------------------------------------------------
# DatasetValidator
# ---------------------------------------------------------------------------

class DatasetValidator:
    """Validate and clean JSONL training datasets."""

    REQUIRED_ROLES = {"system", "user", "assistant"}

    def __init__(
        self,
        min_response_length: int = 50,
        max_response_length: int = 10000,
        near_duplicate_threshold: float = 0.85,
    ):
        self.min_response_length = min_response_length
        self.max_response_length = max_response_length
        self.near_duplicate_threshold = near_duplicate_threshold

    def validate(self, filepath: str) -> Dict[str, Any]:
        """Validate a JSONL dataset file.

        Returns a comprehensive report dict with:
        - statistics (total, valid, invalid, duplicate, etc.)
        - issues list
        - per-line validity
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        issues: List[ValidationIssue] = []
        entries: List[Dict[str, Any]] = []
        valid_entries: List[Dict[str, Any]] = []
        line_validity: List[bool] = []

        # Duplicate tracking
        exact_hashes: Dict[str, int] = {}  # hash -> first line
        near_dup_sets: List[Tuple[int, Set[str]]] = []

        # Stats
        stats = {
            "total_lines": 0,
            "valid": 0,
            "invalid": 0,
            "parse_errors": 0,
            "missing_roles": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "too_short": 0,
            "too_long": 0,
            "empty_content": 0,
            "response_lengths": [],
            "topic_words": [],
        }

        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, raw_line in enumerate(f, start=1):
                stats["total_lines"] += 1
                raw_line = raw_line.strip()

                if not raw_line:
                    issues.append(ValidationIssue(
                        line_num, "warning", "EMPTY_LINE", "Empty line"
                    ))
                    line_validity.append(False)
                    stats["invalid"] += 1
                    continue

                # Parse JSON
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError as e:
                    issues.append(ValidationIssue(
                        line_num, "error", "PARSE_ERROR",
                        f"Invalid JSON: {e}"
                    ))
                    line_validity.append(False)
                    stats["parse_errors"] += 1
                    stats["invalid"] += 1
                    continue

                entries.append(entry)
                entry_valid = True

                # Check messages structure
                messages = entry.get("messages")
                if not isinstance(messages, list):
                    issues.append(ValidationIssue(
                        line_num, "error", "NO_MESSAGES",
                        "Missing or invalid 'messages' field"
                    ))
                    entry_valid = False
                    stats["invalid"] += 1
                    line_validity.append(False)
                    continue

                # Check roles
                roles_present = set()
                assistant_content = ""
                user_content = ""
                has_empty = False

                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    roles_present.add(role)

                    if role == "assistant":
                        assistant_content = content or ""
                    elif role == "user":
                        user_content = content or ""

                    if not content or not content.strip():
                        has_empty = True

                missing_roles = self.REQUIRED_ROLES - roles_present
                if missing_roles:
                    issues.append(ValidationIssue(
                        line_num, "error", "MISSING_ROLES",
                        f"Missing roles: {missing_roles}"
                    ))
                    entry_valid = False
                    stats["missing_roles"] += 1

                if has_empty:
                    issues.append(ValidationIssue(
                        line_num, "warning", "EMPTY_CONTENT",
                        "One or more messages have empty content"
                    ))
                    stats["empty_content"] += 1

                # Response length
                resp_len = len(assistant_content.split())
                stats["response_lengths"].append(resp_len)

                if resp_len < self.min_response_length:
                    issues.append(ValidationIssue(
                        line_num, "warning", "TOO_SHORT",
                        f"Assistant response too short: {resp_len} words "
                        f"(min: {self.min_response_length})"
                    ))
                    stats["too_short"] += 1

                if resp_len > self.max_response_length:
                    issues.append(ValidationIssue(
                        line_num, "warning", "TOO_LONG",
                        f"Assistant response too long: {resp_len} words "
                        f"(max: {self.max_response_length})"
                    ))
                    stats["too_long"] += 1

                # Exact duplicate check (on combined user+assistant)
                combined_text = user_content + " " + assistant_content
                h = _text_hash(combined_text)
                if h in exact_hashes:
                    issues.append(ValidationIssue(
                        line_num, "warning", "EXACT_DUPLICATE",
                        f"Exact duplicate of line {exact_hashes[h]}"
                    ))
                    stats["exact_duplicates"] += 1
                    entry_valid = False
                else:
                    exact_hashes[h] = line_num

                # Near-duplicate check (Jaccard on user prompt)
                if user_content:
                    user_words = _word_set(user_content)
                    for prev_line, prev_words in near_dup_sets:
                        sim = _jaccard_similarity(user_words, prev_words)
                        if sim >= self.near_duplicate_threshold:
                            issues.append(ValidationIssue(
                                line_num, "info", "NEAR_DUPLICATE",
                                f"Near-duplicate of line {prev_line} "
                                f"(Jaccard: {sim:.3f})"
                            ))
                            stats["near_duplicates"] += 1
                            break
                    near_dup_sets.append((line_num, user_words))

                # Topic extraction
                topic_words = _extract_topic_words(user_content + " " + assistant_content)
                stats["topic_words"].extend(topic_words)

                if entry_valid:
                    stats["valid"] += 1
                    valid_entries.append(entry)
                    line_validity.append(True)
                else:
                    stats["invalid"] += 1
                    line_validity.append(False)

        # Concept diversity
        topic_counts = Counter(stats["topic_words"])
        total_topics = len(set(stats["topic_words"]))
        top_topics = topic_counts.most_common(20)

        # Concentration ratio: if top-3 topics dominate, diversity is low
        if topic_counts:
            top3_count = sum(c for _, c in topic_counts.most_common(3))
            total_count = sum(topic_counts.values())
            concentration = top3_count / total_count if total_count else 0
        else:
            concentration = 0

        if concentration > 0.5:
            top_kw = ", ".join(w for w, _ in topic_counts.most_common(3))
            issues.append(ValidationIssue(
                0, "warning", "LOW_DIVERSITY",
                f"Dataset is concentrated on few topics ({concentration:.0%} "
                f"in top-3: {top_kw}). Consider adding more diverse examples."
            ))

        # Build response length stats
        lengths = stats["response_lengths"]
        length_stats = {}
        if lengths:
            lengths_sorted = sorted(lengths)
            length_stats = {
                "min": lengths_sorted[0],
                "max": lengths_sorted[-1],
                "mean": round(sum(lengths) / len(lengths), 1),
                "median": lengths_sorted[len(lengths) // 2],
                "p10": lengths_sorted[int(len(lengths) * 0.1)],
                "p90": lengths_sorted[int(len(lengths) * 0.9)],
            }

        report = {
            "filepath": str(filepath),
            "total_lines": stats["total_lines"],
            "valid": stats["valid"],
            "invalid": stats["invalid"],
            "parse_errors": stats["parse_errors"],
            "missing_roles": stats["missing_roles"],
            "exact_duplicates": stats["exact_duplicates"],
            "near_duplicates": stats["near_duplicates"],
            "too_short": stats["too_short"],
            "too_long": stats["too_long"],
            "empty_content": stats["empty_content"],
            "unique_topics": total_topics,
            "topic_concentration": round(concentration, 4),
            "top_topics": top_topics,
            "response_length_stats": length_stats,
            "issues": issues,
            "line_validity": line_validity,
            "valid_entries": valid_entries,
        }

        return report

    # -- auto-filter -------------------------------------------------------

    def filter_dataset(
        self,
        filepath: str,
        output_path: str,
        remove_duplicates: bool = True,
        remove_short: bool = True,
        remove_long: bool = True,
        remove_invalid: bool = True,
    ) -> Dict[str, int]:
        """Validate and write a cleaned dataset.

        Returns stats about the filtering.
        """
        report = self.validate(filepath)
        issues_by_line: Dict[int, List[ValidationIssue]] = defaultdict(list)
        for issue in report["issues"]:
            issues_by_line[issue.line_num].append(issue)

        kept = 0
        removed = 0
        reasons: Dict[str, int] = defaultdict(int)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(filepath, "r", encoding="utf-8") as fin, \
             open(output_path, "w", encoding="utf-8") as fout:

            seen_hashes: Set[str] = set()

            for line_num, raw_line in enumerate(fin, start=1):
                raw_line = raw_line.strip()
                if not raw_line:
                    removed += 1
                    reasons["empty_line"] += 1
                    continue

                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    if remove_invalid:
                        removed += 1
                        reasons["parse_error"] += 1
                        continue

                messages = entry.get("messages", [])
                if not isinstance(messages, list):
                    if remove_invalid:
                        removed += 1
                        reasons["no_messages"] += 1
                        continue

                roles = {m.get("role") for m in messages}
                if self.REQUIRED_ROLES - roles:
                    if remove_invalid:
                        removed += 1
                        reasons["missing_roles"] += 1
                        continue

                # Extract texts
                assistant_text = ""
                user_text = ""
                for m in messages:
                    if m.get("role") == "assistant":
                        assistant_text = m.get("content", "")
                    elif m.get("role") == "user":
                        user_text = m.get("content", "")

                # Length checks
                word_count = len(assistant_text.split())
                if remove_short and word_count < self.min_response_length:
                    removed += 1
                    reasons["too_short"] += 1
                    continue
                if remove_long and word_count > self.max_response_length:
                    removed += 1
                    reasons["too_long"] += 1
                    continue

                # Duplicate check
                if remove_duplicates:
                    h = _text_hash(user_text + " " + assistant_text)
                    if h in seen_hashes:
                        removed += 1
                        reasons["duplicate"] += 1
                        continue
                    seen_hashes.add(h)

                fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
                kept += 1

        return {
            "input_lines": report["total_lines"],
            "kept": kept,
            "removed": removed,
            "removal_reasons": dict(reasons),
        }

    # -- report formatting -------------------------------------------------

    def format_report(self, report: Dict[str, Any]) -> str:
        """Format validation report as readable text."""
        lines: List[str] = []
        lines.append("=" * 70)
        lines.append("  DATASET VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append(f"  File: {report['filepath']}")
        lines.append("")

        # Summary
        lines.append("-" * 70)
        lines.append("  SUMMARY")
        lines.append("-" * 70)
        lines.append(f"    Total lines:        {report['total_lines']}")
        lines.append(f"    Valid:              {report['valid']}")
        lines.append(f"    Invalid:            {report['invalid']}")
        lines.append(f"    Parse errors:       {report['parse_errors']}")
        lines.append(f"    Missing roles:      {report['missing_roles']}")
        lines.append(f"    Exact duplicates:   {report['exact_duplicates']}")
        lines.append(f"    Near duplicates:    {report['near_duplicates']}")
        lines.append(f"    Too short:          {report['too_short']}")
        lines.append(f"    Too long:           {report['too_long']}")
        lines.append(f"    Empty content:      {report['empty_content']}")

        # Length stats
        ls = report.get("response_length_stats", {})
        if ls:
            lines.append("")
            lines.append("-" * 70)
            lines.append("  RESPONSE LENGTH (words)")
            lines.append("-" * 70)
            lines.append(f"    Min:    {ls.get('min', 'N/A')}")
            lines.append(f"    Max:    {ls.get('max', 'N/A')}")
            lines.append(f"    Mean:   {ls.get('mean', 'N/A')}")
            lines.append(f"    Median: {ls.get('median', 'N/A')}")
            lines.append(f"    P10:    {ls.get('p10', 'N/A')}")
            lines.append(f"    P90:    {ls.get('p90', 'N/A')}")

        # Diversity
        lines.append("")
        lines.append("-" * 70)
        lines.append("  TOPIC DIVERSITY")
        lines.append("-" * 70)
        lines.append(f"    Unique topic words:   {report.get('unique_topics', 0)}")
        lines.append(f"    Top-3 concentration:  {report.get('topic_concentration', 0):.1%}")
        top_topics = report.get("top_topics", [])
        if top_topics:
            lines.append("    Top topics:")
            for word, count in top_topics[:10]:
                lines.append(f"      {word:<20s}  {count}")

        # Issues
        issues = report.get("issues", [])
        error_issues = [i for i in issues if i.severity == "error"]
        warning_issues = [i for i in issues if i.severity == "warning"]

        if error_issues:
            lines.append("")
            lines.append("-" * 70)
            lines.append(f"  ERRORS ({len(error_issues)})")
            lines.append("-" * 70)
            for issue in error_issues[:20]:
                lines.append(f"    {issue}")
            if len(error_issues) > 20:
                lines.append(f"    ... and {len(error_issues) - 20} more errors")

        if warning_issues:
            lines.append("")
            lines.append("-" * 70)
            lines.append(f"  WARNINGS ({len(warning_issues)})")
            lines.append("-" * 70)
            for issue in warning_issues[:20]:
                lines.append(f"    {issue}")
            if len(warning_issues) > 20:
                lines.append(f"    ... and {len(warning_issues) - 20} more warnings")

        # Verdict
        lines.append("")
        lines.append("-" * 70)
        if (report["invalid"] == 0
                and report["exact_duplicates"] == 0
                and report.get("near_duplicates", 0) == 0
                and report.get("too_short", 0) == 0
                and report.get("empty_content", 0) == 0):
            lines.append("  VERDICT: PASS - Dataset is clean")
        elif report["invalid"] > report["total_lines"] * 0.1:
            lines.append("  VERDICT: FAIL - Too many invalid entries (>10%)")
        else:
            lines.append("  VERDICT: WARN - Some issues found, consider filtering")
        lines.append("-" * 70)

        lines.append("=" * 70)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Codette Dataset Validator - check and clean JSONL training data"
    )
    parser.add_argument(
        "dataset",
        help="Path to JSONL dataset file",
    )
    parser.add_argument(
        "--filter", "-f",
        metavar="OUTPUT",
        default=None,
        help="Auto-filter and write clean dataset to OUTPUT path",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=50,
        help="Minimum assistant response length in words (default: 50)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=10000,
        help="Maximum assistant response length in words (default: 10000)",
    )
    parser.add_argument(
        "--duplicate-threshold",
        type=float,
        default=0.85,
        help="Jaccard similarity threshold for near-duplicates (default: 0.85)",
    )
    parser.add_argument(
        "--json-report",
        metavar="PATH",
        default=None,
        help="Save report as JSON to this path",
    )

    args = parser.parse_args()

    validator = DatasetValidator(
        min_response_length=args.min_length,
        max_response_length=args.max_length,
        near_duplicate_threshold=args.duplicate_threshold,
    )

    print(f"Validating: {args.dataset}\n")
    report = validator.validate(args.dataset)
    print(validator.format_report(report))

    if args.json_report:
        # Remove non-serialisable items
        save_report = {k: v for k, v in report.items()
                       if k not in ("issues", "line_validity", "valid_entries")}
        save_report["issue_count"] = len(report["issues"])
        save_report["issues_summary"] = [repr(i) for i in report["issues"][:50]]
        os.makedirs(os.path.dirname(args.json_report) or ".", exist_ok=True)
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(save_report, f, indent=2, default=str)
        print(f"\nJSON report saved to: {args.json_report}")

    if args.filter:
        print(f"\nFiltering dataset -> {args.filter}")
        filter_stats = validator.filter_dataset(args.dataset, args.filter)
        print(f"  Input lines:  {filter_stats['input_lines']}")
        print(f"  Kept:         {filter_stats['kept']}")
        print(f"  Removed:      {filter_stats['removed']}")
        for reason, count in filter_stats["removal_reasons"].items():
            print(f"    - {reason}: {count}")


if __name__ == "__main__":
    main()
