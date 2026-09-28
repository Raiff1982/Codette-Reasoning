"""Collect the BeliefRevisionSystem suite.

Its tests live inside reasoning_forge/belief_revision_system.py, which pytest's
default test_*.py pattern never collects, so a normal suite run skipped all of
them. Importing the TestCase here makes pytest run them.
"""

from reasoning_forge.belief_revision_system import (  # noqa: F401
    TestBeliefRevisionSystem,
)
