"""
TimeTravelLens — three-path test suite.

Run from the repo root:
    python tests/test_timelens.py

Paths exercised:
  A) Direct lens with handcrafted InstitutionalState     (no extraction, zero deps)
  B) InstitutionalExtractor from realistic text          (needs dateutil)
  C) Live HTTP endpoint /api/time_travel/analyze         (needs server running on 7860)
"""

import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ── Path fix ──────────────────────────────────────────────────────────────────
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reasoning_forge.time_travel_lens import (
    ActorGap,
    ClosureClass,
    InstitutionalContextDetector,
    InstitutionalState,
    TimeTravelConfig,
    TimeTravelLens,
    TimestampLadder,
)

_EPOCH = datetime(1970, 1, 1)


def days(year: int, month: int, day: int) -> float:
    return (datetime(year, month, day) - _EPOCH).total_seconds() / 86400.0


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    line = f"  [{status}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return condition


# ── Path A: direct lens ───────────────────────────────────────────────────────

def test_direct_lens() -> int:
    """
    Boeing 737 MAX style scenario.
    Engineers identified MCAS issues in March 2019.
    FAA formally grounded the fleet in March 2019 (same month = gap near 0).
    Use a suppressed variant: internal fix attempt in Oct 2018, grounding March 2019.
    """
    print("\n══ Path A: direct lens (handcrafted InstitutionalState) ══")

    # Engineers knew at Lion Air crash (Oct 2018) → grounding Mar 2019: gap=135 days.
    # Executives delayed formal acknowledgement until Jun 2019: gap=215 days.
    # Variance([135, 215]) = 1600 >> τ_V=50 → high_preemption_zone triggers.
    state = InstitutionalState(
        state_id="test-737max",
        ladder=TimestampLadder(
            t_op=days(2018, 10, 29),    # Lion Air crash — Boeing knew of MCAS issue
            t_inst=days(2019, 3, 13),   # FAA grounding order
        ),
        closure_class=ClosureClass.SUPPRESSED,
        unfolding_energy=45.0,          # high — prolonged concealment
        influence_over_time=[10.0] * 12,  # 12 months × 10 = 120 > τ_I(100)
        actor_gaps=[
            ActorGap("engineers",  t_op_i=days(2018, 10, 29), t_inst_i=days(2019, 3, 13)),
            ActorGap("executives", t_op_i=days(2018, 10, 29), t_inst_i=days(2019, 6, 1)),
            ActorGap("regulators", t_op_i=None,               t_inst_i=days(2019, 3, 13)),
        ],
        registration_fidelity_memo="Internal MCAS memos suppressed before FAA disclosure.",
    )

    lens = TimeTravelLens(config=TimeTravelConfig.default())
    obs = lens.observe(state)

    print(f"\n  Observation bundle:")
    for k, v in obs.items():
        print(f"    {k}: {v}")

    expected_gap = days(2019, 3, 13) - days(2018, 10, 29)
    failures = 0

    failures += not check("preemption_gap_days ~135",
                          abs(obs["preemption_gap_days"] - round(expected_gap, 2)) < 0.1,
                          f"got {obs['preemption_gap_days']}")
    failures += not check("closure_class == suppressed",
                          obs["closure_class"] == "suppressed")
    failures += not check("closure_score == 0.24",
                          obs["closure_score"] == 0.24)
    failures += not check("rupture == True",   obs["rupture"])
    failures += not check("beacon == True",    obs["beacon"],
                          "influence=120 > τ_I=100")
    failures += not check("practical_non_closure == True",
                          obs["practical_non_closure"],
                          "E_u=45 > τ_E=10")
    failures += not check("high_preemption_zone == True",
                          obs["high_preemption_zone"],
                          "Π>30, C<0.5, Var_i>50")
    failures += not check("actor_gaps has 2 finite entries",
                          sum(1 for v in obs["actor_gaps"].values()
                              if v is not None) == 2)

    return failures


# ── Path B: InstitutionalExtractor ────────────────────────────────────────────

SAMPLE_TEXT = """\
On 2020-01-15, engineers at MedDevice Corp internally discovered a critical
software defect in their cardiac monitor firmware that could suppress alarm
notifications under certain conditions.  Management was immediately aware but
kept the issue secret from regulators to avoid a recall.

The FDA was not notified.  The defect was concealed while the company quietly
patched the firmware for new units only.  Existing devices remained in the field.

On 2021-09-15, a whistleblower filed a formal disclosure with the FDA.
Following the regulatory filing and investigation, MedDevice Corp officially
acknowledged the defect and announced a full recall on 2021-10-03.
The investigation is now closed.
"""

def test_extractor() -> int:
    print("\n══ Path B: InstitutionalExtractor from text ══")
    print(f"\n  Input text ({len(SAMPLE_TEXT)} chars):")
    for line in SAMPLE_TEXT.strip().split("\n"):
        if line.strip():
            print(f"    {line}")

    # Gate check first
    is_rel = InstitutionalContextDetector.is_relevant(SAMPLE_TEXT)
    print(f"\n  InstitutionalContextDetector.is_relevant() → {is_rel}")

    try:
        from reasoning_forge.institutional_extractor import InstitutionalExtractor
    except ImportError as e:
        print(f"  [SKIP] InstitutionalExtractor import failed: {e}")
        return 0

    ext = InstitutionalExtractor()
    state, conf = ext.extract(SAMPLE_TEXT)

    print(f"\n  Extraction confidence: {conf}")

    if state is None:
        print(f"  [{FAIL}] No state extracted (confidence too low)")
        return 1

    lens = TimeTravelLens(config=TimeTravelConfig.default())
    obs = lens.observe(state)

    print(f"\n  Observation bundle:")
    for k, v in obs.items():
        print(f"    {k}: {v}")

    failures = 0
    failures += not check("relevant gate fired",     is_rel)
    failures += not check("confidence >= 0.3",       conf >= 0.3,  f"got {conf}")
    failures += not check("preemption_gap finite",
                          obs["preemption_gap_days"] is not None,
                          str(obs["preemption_gap_days"]))
    failures += not check("closure_class extracted",
                          obs["closure_class"] in ("suppressed", "closed", "drift"))
    failures += not check("rupture detected",        obs["rupture"])
    return failures


# ── Path C: live HTTP endpoint ────────────────────────────────────────────────

def test_http_endpoint(port: int = 7860) -> int:
    print(f"\n══ Path C: live HTTP /api/time_travel/analyze (port {port}) ══")

    encoded = urllib.parse.quote(SAMPLE_TEXT, safe="")
    url = f"http://localhost:{port}/api/time_travel/analyze?text={encoded}"

    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            body = json.loads(r.read())
    except urllib.error.URLError as e:
        print(f"  [SKIP] Server not reachable: {e}")
        print(f"  Start Codette first, then re-run to test this path.")
        return 0

    print(f"\n  HTTP response:")
    print(json.dumps(body, indent=4))

    failures = 0
    failures += not check("status == ok",  body.get("status") == "ok",
                          f"got {body.get('status')}")
    if body.get("status") == "ok":
        m = body.get("metrics", {})
        failures += not check("metrics.preemption_gap_days present",
                              "preemption_gap_days" in m)
        failures += not check("metrics.closure_class present",
                              "closure_class" in m)
        failures += not check("metrics.rupture present", "rupture" in m)
    return failures


# ── Chat query guide ──────────────────────────────────────────────────────────

CHAT_PROMPTS = [
    (
        "Full scenario (high confidence)",
        "In March 2018, executives at PharmaCo internally discovered that their blood "
        "pressure drug caused liver damage. Management suppressed the findings and "
        "concealed them from the FDA. The company failed to disclose the defect "
        "until October 2021 when a whistleblower filed a regulatory report and "
        "the FDA opened an investigation.",
    ),
    (
        "Cover-up with actors",
        "Boeing engineers were aware of the MCAS software defect in October 2018 "
        "after the Lion Air crash. Management and executives kept the issue secret "
        "from regulators. The FAA formally grounded the 737 MAX in March 2019 "
        "after a second crash. Compensation settlements followed.",
    ),
    (
        "Minimal trigger (2 keywords)",
        "The company knew about the defect but suppressed the investigation.",
    ),
    (
        "Will NOT trigger (only 1 keyword)",
        "Tell me about corporate history.",
    ),
]

def print_chat_guide():
    print("\n══ Chat prompts that trigger TimeTravelLens ══")
    print("  Paste these into Codette's chat box.\n"
          "  After the response, click the 🕰 TimeLens button to see metrics.\n")
    for i, (label, prompt) in enumerate(CHAT_PROMPTS, 1):
        relevant = InstitutionalContextDetector.is_relevant(prompt)
        marker = "✓ TRIGGERS" if relevant else "✗ won't trigger"
        print(f"  [{i}] {label}  →  {marker}")
        print(f"      \"{prompt[:90]}{'...' if len(prompt) > 90 else ''}\"")
        print()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7860

    total_failures = 0
    total_failures += test_direct_lens()
    total_failures += test_extractor()
    total_failures += test_http_endpoint(port)
    print_chat_guide()

    print(f"\n{'═' * 54}")
    if total_failures == 0:
        print(f"  All checks passed.")
    else:
        print(f"  {total_failures} check(s) failed.")
    sys.exit(0 if total_failures == 0 else 1)
