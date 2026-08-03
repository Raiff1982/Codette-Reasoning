#!/usr/bin/env python3
"""Quick test of query classifier to verify SIMPLE/MEDIUM/COMPLEX routing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

# 2026-08-03: this file was a diagnostic SCRIPT wearing a test's name.
#
# Its module body ran on import (printing a report), and `test_category(queries,
# expected)` was collected by pytest as a test whose two parameters it tried to
# resolve as fixtures — `fixture 'queries' not found`. That is the "1 error"
# that sat in the suite: the query classifier, which decides how everything is
# routed, had NO automated coverage at all while appearing to have some.
#
# Converted to real parametrized tests. Every one of the 30 original queries is
# preserved verbatim, and the exact expectations are asserted rather than
# counted and printed — measured at 30/30 (100%) before the conversion, so
# asserting exact classification is honest rather than aspirational.
#
# The report is still available: `python tests/test_classifier.py`.

import pytest


def _check_category(queries, expected):
    """Classify a category and return (correct, failures). Used by both paths."""
    correct, failures = 0, []
    for query in queries:
        result = classifier.classify(query)
        if result == expected:
            correct += 1
        else:
            failures.append((query, result, expected))
    return correct, failures


@pytest.mark.parametrize("query", simple_queries)
def test_simple_queries_classify_simple(query):
    assert classifier.classify(query) == QueryComplexity.SIMPLE


@pytest.mark.parametrize("query", medium_queries)
def test_medium_queries_classify_medium(query):
    assert classifier.classify(query) == QueryComplexity.MEDIUM


@pytest.mark.parametrize("query", complex_queries)
def test_complex_queries_classify_complex(query):
    assert classifier.classify(query) == QueryComplexity.COMPLEX


def test_overall_classifier_accuracy():
    """Guards the aggregate, so a broad regression cannot hide behind one case."""
    total_correct = 0
    all_failures = []
    for queries, expected in (
        (simple_queries, QueryComplexity.SIMPLE),
        (medium_queries, QueryComplexity.MEDIUM),
        (complex_queries, QueryComplexity.COMPLEX),
    ):
        correct, failures = _check_category(queries, expected)
        total_correct += correct
        all_failures.extend(failures)
    total = len(simple_queries) + len(medium_queries) + len(complex_queries)
    assert total_correct == total, (
        f"{total_correct}/{total} correct; misclassified: "
        + "; ".join(f"{q!r} -> {got.value} (want {want.value})"
                    for q, got, want in all_failures)
    )


def _report() -> None:
    """The original printed diagnostic, preserved for direct invocation."""
    print("=" * 80)
    print("TESTING QUERY CLASSIFIER")
    print("=" * 80)
    total_correct = 0
    for label, queries, expected in (
        ("SIMPLE", simple_queries, QueryComplexity.SIMPLE),
        ("MEDIUM", medium_queries, QueryComplexity.MEDIUM),
        ("COMPLEX", complex_queries, QueryComplexity.COMPLEX),
    ):
        print(f"\n[{label}] Queries (should be classified as {label}):")
        for query in queries:
            result = classifier.classify(query)
            status = "[OK]" if result == expected else "[FAIL]"
            print(f"  {status} {result.value.upper():8} | {query[:60]}")
        correct, _ = _check_category(queries, expected)
        total_correct += correct
        print(f"  Result: {correct}/{len(queries)} correct\n")

    total = len(simple_queries) + len(medium_queries) + len(complex_queries)
    print("=" * 80)
    print(f"OVERALL: {total_correct}/{total} correct ({100*total_correct/total:.0f}%)")
    print("=" * 80)


if __name__ == "__main__":
    _report()
