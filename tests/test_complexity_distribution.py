"""One category was split across two keys by how an enum was stringified."""
from reasoning_forge.unified_memory import UnifiedMemory


def test_enum_spelling_does_not_split_a_category(tmp_path):
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    m = UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)
    for i in range(3):
        m.store(f"q{i}", f"answer number {i} is long enough", complexity="QueryComplexity.MEDIUM")
    for i in range(2):
        m.store(f"p{i}", f"reply number {i} is long enough", complexity="MEDIUM")
    m.store("s", "a simple reply that is long enough", complexity="QueryComplexity.SIMPLE")
    dist = m.complexity_distribution()
    assert dist == {"MEDIUM": 5, "SIMPLE": 1}
    assert list(dist) == ["MEDIUM", "SIMPLE"]       # still ordered by count
