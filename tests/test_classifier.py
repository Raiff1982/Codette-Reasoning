#!/usr/bin/env python3
"""Quick test of query classifier to verify SIMPLE/MEDIUM/COMPLEX routing."""

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

print("=" * 80)
print("TESTING QUERY CLASSIFIER")
print("=" * 80)

def test_category(queries, expected):
    """Test a category of queries."""
    correct = 0
    for query in queries:
        result = classifier.classify(query)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} {result.value.upper():8} | {query[:60]}")
        if result == expected:
            correct += 1
    return correct

print("\n[SIMPLE] Queries (should be classified as SIMPLE):")
simple_correct = test_category(simple_queries, QueryComplexity.SIMPLE)
print(f"  Result: {simple_correct}/{len(simple_queries)} correct\n")

print("[MEDIUM] Queries (should be classified as MEDIUM):")
medium_correct = test_category(medium_queries, QueryComplexity.MEDIUM)
print(f"  Result: {medium_correct}/{len(medium_queries)} correct\n")

print("[COMPLEX] Queries (should be classified as COMPLEX):")
complex_correct = test_category(complex_queries, QueryComplexity.COMPLEX)
print(f"  Result: {complex_correct}/{len(complex_queries)} correct\n")

print("=" * 80)
total_correct = simple_correct + medium_correct + complex_correct
total = len(simple_queries) + len(medium_queries) + len(complex_queries)
print(f"OVERALL: {total_correct}/{total} correct ({100*total_correct/total:.0f}%)")
print("=" * 80)
