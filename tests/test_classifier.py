#!/usr/bin/env python3
"""Quick test of query classifier to verify SIMPLE/MEDIUM/COMPLEX routing.

2026-08-08: this was written as a diagnostic *script*, not a pytest module, but
it lives in `tests/` and its helper was named `test_category(queries, expected)`.
pytest therefore collected the helper as a test, saw two parameters it could not
match to fixtures, and raised the `fixture 'queries' not found` collection error
that has been carried on every handoff since 2026-08-04. Nothing was broken: the
classifier scores 30/30 on these queries. The error was a naming collision.

The script is preserved exactly — run it directly and it prints the same report.
The helper is now `_check_category` so pytest leaves it alone, and the assertions
it always implied are written out as real tests below.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from reasoning_forge.query_classifier import QueryClassifier, QueryComplexity

# Test queries from benchmark
classifier = QueryClassifier()

simple_queries = [
    "What is the speed of light?",
    "Define entropy",
    "Who is Albert Einstein?",
    "What year was the Internet invented?",
    "How high is Mount Everest?",
    "What is the chemical formula for water?",
    "Define photosynthesis",
    "Who wrote Romeo and Juliet?",
    "What is the capital of France?",
    "How fast can a cheetah run?",
]

medium_queries = [
    "How does quantum mechanics relate to consciousness?",
    "What are the implications of artificial intelligence?",
    "Compare classical and quantum computing",
    "How do neural networks learn?",
    "What is the relationship between energy and mass?",
    "How does evolution explain biodiversity?",
    "What are the main differences between mitochondria and chloroplasts?",
    "How does feedback regulate biological systems?",
    "What is the connection between sleep and memory consolidation?",
    "How do economic systems balance growth and sustainability?",
]

complex_queries = [
    "Can machines be truly conscious?",
    "What is the nature of free will and how does it relate to determinism?",
    "Is artificial intelligence the future of humanity?",
    "How should AI be ethically governed?",
    "What makes something morally right or wrong?",
    "Can subjective experience be measured objectively?",
    "How does quantum mechanics challenge our understanding of reality?",
    "What is the relationship between language and thought?",
    "How should society balance individual freedom with collective good?",
    "Is human consciousness unique, or could machines achieve it?",
]

def _check_category(queries, expected):
    """Classify a category of queries, printing each result. Returns hit count."""
    correct = 0
    for query in queries:
        result = classifier.classify(query)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} {result.value.upper():8} | {query[:60]}")
        if result == expected:
            correct += 1
    return correct


# ---------------------------------------------------------------------------
# The assertions the script always implied
# ---------------------------------------------------------------------------

_CASES = (
    [(q, QueryComplexity.SIMPLE) for q in simple_queries]
    + [(q, QueryComplexity.MEDIUM) for q in medium_queries]
    + [(q, QueryComplexity.COMPLEX) for q in complex_queries]
)


@pytest.mark.parametrize("query,expected", _CASES, ids=[q[:40] for q, _ in _CASES])
def test_query_classifies_to_expected_complexity(query, expected):
    assert classifier.classify(query) == expected


def test_overall_accuracy_is_total():
    """All 30 measured 2026-08-08. This is allowed to fall — that is the point."""
    correct = sum(1 for q, expected in _CASES if classifier.classify(q) == expected)
    assert correct == len(_CASES)


if __name__ == "__main__":
    print("=" * 80)
    print("TESTING QUERY CLASSIFIER")
    print("=" * 80)

    print("\n[SIMPLE] Queries (should be classified as SIMPLE):")
    simple_correct = _check_category(simple_queries, QueryComplexity.SIMPLE)
    print(f"  Result: {simple_correct}/{len(simple_queries)} correct\n")

    print("[MEDIUM] Queries (should be classified as MEDIUM):")
    medium_correct = _check_category(medium_queries, QueryComplexity.MEDIUM)
    print(f"  Result: {medium_correct}/{len(medium_queries)} correct\n")

    print("[COMPLEX] Queries (should be classified as COMPLEX):")
    complex_correct = _check_category(complex_queries, QueryComplexity.COMPLEX)
    print(f"  Result: {complex_correct}/{len(complex_queries)} correct\n")

    print("=" * 80)
    total_correct = simple_correct + medium_correct + complex_correct
    total = len(simple_queries) + len(medium_queries) + len(complex_queries)
    print(f"OVERALL: {total_correct}/{total} correct ({100*total_correct/total:.0f}%)")
    print("=" * 80)
