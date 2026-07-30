"""The Charter as fixed stars.

Everything else Codette navigates by moves: recalled turns slide, cocoons rank by
recency, the continuity summary advances every turn. The Charter does not. These
tests keep it that way — parsed from the document rather than copied into Python,
and reported as a bearing rather than a course.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.constellation import (
    CHARTER_PATH,
    Sky,
    describe_bearing,
    load_constellation,
    visible_from,
)


def test_the_charter_loads_as_seven_stars():
    sky = load_constellation()
    assert sky, "the charter should load"
    assert len(sky.stars) == 7
    assert [s.number for s in sky.stars] == [1, 2, 3, 4, 5, 6, 7]


def test_honesty_markers_are_carried_through_not_reinterpreted():
    sky = load_constellation()
    by_number = {s.number: s for s in sky.stars}

    assert by_number[4].status == "PARTWAY"
    assert by_number[5].status == "HAVE IT"
    assert by_number[1].status == "REFRAME"


def test_a_pillar_without_a_canonical_marker_is_unmarked_not_guessed():
    """Pillars 3, 6 and 7 carry prose, not one of the three markers."""
    sky = load_constellation()
    by_number = {s.number: s for s in sky.stars}
    assert by_number[6].status is None


def test_missing_charter_yields_an_empty_sky_not_remembered_stars():
    sky = load_constellation(Path("does/not/exist/CHARTER.md"))
    assert not sky
    assert sky.stars == []
    assert "not assumed" in sky.note


def test_bearing_finds_provenance_pillar_from_attribution_language():
    stars = visible_from(
        "provenance and dated priority so attribution is airtight and nothing "
        "is scrubbed or stolen"
    )
    assert 7 in {s.number for s in stars}


def test_bearing_finds_the_honesty_pillar_from_fabrication_language():
    stars = visible_from(
        "the response fabricated a claim that was never measured and the "
        "hallucination guard did not mark it"
    )
    assert 2 in {s.number for s in stars}


def test_empty_passage_reaches_for_nothing():
    assert visible_from("   ") == []
    assert visible_from("") == []


def test_bearing_never_states_a_course():
    """A compass, not a cage — the reading describes, it does not direct."""
    reading = describe_bearing("transparency and provenance and honest uncertainty")
    lowered = reading.lower()
    for directive in ("should", "must", "you need to", "recommend", "off course"):
        assert directive not in lowered
    assert "no course implied" in lowered


def test_stars_are_read_from_disk_not_duplicated_in_code():
    """The document is the map. A second copy would be a second map."""
    source = Path(__file__).resolve().parent.parent / "reasoning_forge" / "constellation.py"
    body = source.read_text(encoding="utf-8")
    assert "Never stolen or lost again" not in body
    assert CHARTER_PATH.name == "CODETTE_CHARTER.md"


def test_empty_sky_bearing_explains_itself():
    sky = Sky([], None, "no charter — sky is empty, not assumed")
    assert "not assumed" in describe_bearing("anything at all", sky)
