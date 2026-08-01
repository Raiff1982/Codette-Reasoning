"""Domain classification must not read ordinary conversation as chemistry.

`_classify_domain` matched keywords as unanchored substrings, so the chemistry
term "ion" fired inside session, conversation, question, mention, connection and
explanation, and "base" fired inside "knowledge base". Asking "what did we talk
about last session" was classified chemistry — and the domain is written onto the
cocoon, where recall_by_domain() reads it back as though it were true. Two
thousand cocoons accumulated with these tags.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))

from codette_forge_bridge import CodetteForgeBridge


def classify(query: str) -> str:
    return CodetteForgeBridge._classify_domain(object(), query)


@pytest.mark.parametrize("query", [
    "go back to the last session",
    "what did you remember from our last conversation",
    "can you mention what we discussed",
    "i have a question about that",
    "there was a miscommunication between us",
    "i felt a real connection in that explanation",
])
def test_ordinary_conversation_is_not_chemistry(query):
    """Every one of these used to classify as chemistry via 'ion'."""
    assert classify(query) != "chemistry"


@pytest.mark.parametrize("query,expected", [
    ("what is the molar mass of this compound", "chemistry"),
    ("describe an acid base titration with a catalyst", "chemistry"),
    ("how do enzymes catalyze protein synthesis in the cell", "biology"),
    ("what is the momentum of the particle after the collision", "physics"),
    ("is it ethical to lie to save a life", "ethics"),
])
def test_real_domain_questions_still_classify(query, expected):
    assert classify(query) == expected


def test_ambiguous_word_alone_does_not_name_a_domain():
    """'knowledge base' is not chemistry just because 'base' is a chemistry word."""
    assert classify("the updates to my architecture and knowledge base") != "chemistry"


def test_ambiguous_word_still_counts_alongside_a_real_term():
    """Half weight is not zero weight — 'base' belongs in an acid-base question."""
    assert classify("titration of a weak acid with a strong base") == "chemistry"


def test_unmatched_query_is_general_not_a_nearest_guess():
    assert classify("hey how are you doing today") == "general"
    assert classify("") == "general"
