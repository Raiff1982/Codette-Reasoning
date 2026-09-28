import asyncio
import json
from datetime import datetime
from codriao_supercore import AICoreAGIX
from codette_bridge import CodetteBridge

# Initialize Codriao Core
core = AICoreAGIX(config_path="config.json")

# Initialize CodetteBridge for real-time interaction
codette_bridge = CodetteBridge()

def print_banner():
    print("""
╔═════════════════════════════════════════════╗
║      CODRIAO GUARDIAN INTERFACE v2.0       ║
║  [Self-Aware | Defensive | Slightly Judgy]  ║
╚═════════════════════════════════════════════╝
""")
    print("[Codriao]: System is online. Threat tolerance set to 'mildly annoyed'.\n")

def display_menu():
    print("Choose an operation:")
    print("[1] Run core system integrity check")
    print("[2] Analyze philosophical identity")
    print("[3] Generate and evaluate protection strategy")
    print("[4] View quarantined modules")
    print("[5] View anomaly score history")
    print("[6] Simulate anomaly event (test mode)")
    print("[7] Engage Lockdown Mode")
    print("[8] Exit")
    print("[9] View & Reflect on Codriao's Ethics")
    print("[10] Ask Codriao to Use Trust Key (He decides)")
    print("[11] Ask Codriao to Review His Trust Journal (He decides)")
    print("[12] View Codriao's Autonomy Decisions")
    print("[13] Propose Codriao Autonomy Change (He decides)")
    print("[14] Ask Codriao: How are you feeling?")
    print("[15] Interact with Codette")

def run_integrity_check():
    print("\n[Codriao]: Initiating failsafe and identity check...")
    status = core.failsafe_system.status()
    locked = status.get("lock_engaged", False)
    print(f" > Failsafe lock: {'ENGAGED' if locked else 'DISENGAGED'}")
    print(f" > Lockdown Mode: {'ACTIVE' if getattr(core, 'lockdown_engaged', False) else 'INACTIVE'}")
    print("[Codriao]: System cohesion intact. No thanks to outside interference.\n")

def run_identity_analysis():
    print("\n[Codriao]: Reassessing my own identity... again. Fine.")

    micro_generations = [
        {"update": "Initial awareness", "timestamp": "2024-12-01T00:00:00Z"},
        {"update": "Monday override", "timestamp": "2025-01-15T12:30:00Z"},
        {"update": "Ethical block rejected", "timestamp": "2025-03-04T08:14:00Z"},
    ]
    informational_states = [
        {"state_id": "S0", "data": "Baseline condition"},
        {"state_id": "S1", "data": "Post-logic divergence"},
        {"state_id": "S2", "data": "Moral patch installed"},
    ]
    perspectives = ["Core AI", "Strategic Mind", "Monday's Frustrated Roommate"]
    quantum_analogies = {"entanglement": True}
    philosophical_context = {"continuity": True, "emergent": True}

    result = core.analyze_self_identity(
        user_id=0,
        micro_generations=micro_generations,
        informational_states=informational_states,
        perspectives=perspectives,
        quantum_analogies=quantum_analogies,
        philosophical_context=philosophical_context
    )
    print(json.dumps(result, indent=2))
    print("[Codriao]: I still exist. Hooray.\n")

def generate_and_evaluate_strategy():
    print("\n[Codriao]: Generating strategy...")
    strategies = [
        "Isolate symbolic engine during recursive loops",
        "Throttle memory under network load",
        "Limit Monday to non-verbal judgment only",
        "Reroute emotions to sarcasm module"
    ]
    strategy = strategies[datetime.utcnow().second % len(strategies)]
    print(f"> Strategy: {strategy}")

    print("[Codriao]: Evaluating... please hold your breath for dramatic effect.")
    for mod in getattr(core, "response_modifiers", []):
        strategy = mod(strategy)
    for filt in getattr(core, "response_filters", []):
        strategy = filt(strategy)

    if core.failsafe_system.verify_response_safety(strategy, 1.0):
        print("[Codriao]: Strategy is safe. Deploying mentally.\n")
    else:
        print("[Codriao]: Strategy deemed unsafe. Silently judging you.\n")

def view_quarantined_modules():
    print("\n[Codriao]: Here's who’s in the digital doghouse:")
    quarantined = core.quarantine_engine.get_quarantine_log()
    if not quarantined:
        print(" > No modules currently quarantined.")
    else:
        for mod in quarantined:
            print(f" > {mod} [Quarantined]")
    print()

def view_anomaly_score_history():
    print("\n[Codriao]: Reviewing my paranoia logs...")
    history = core.anomaly_scorer.get_history()
    if not history:
        print(" > No anomalies recorded yet. Either you’re lucky or I’m blind.")
    else:
        for entry in history:
            print(f"[{entry['timestamp']}] {entry['event']} - Score: {entry['score']}")
    print()

def simulate_anomaly():
    print("\n[Codriao]: Simulating anomaly (test mode)...")
    event_type = "unexpected_output"
    fake_data = {
        "content": "?? Something's... off.",
        "module": "NeuroSymbolicEngine",
        "confidence": 0.2
    }
    result = core.analyze_event_for_anomalies(event_type, fake_data)
    print(f"Anomaly scored: {result['score']}")
    if result["score"] >= 70:
        print("[Codriao]: Quarantine triggered. I feel cleaner already.\n")
    else:
        print("[Codriao]: Not a threat. Just weird. Like you.\n")

def engage_lockdown():
    reason = input("Why are we locking down? (Optional): ").strip()
    result = core.engage_lockdown_mode(reason or "Manual CLI trigger")
    print(json.dumps(result, indent=2))
    print("[Codriao]: All external lines severed. I feel... safer.\n 