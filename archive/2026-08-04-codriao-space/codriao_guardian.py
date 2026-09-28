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
    print("[Codriao]: All external lines severed. I feel... safer.\n")


def view_ethics():
    ethics = core.ethics_core.export_ethics()
    print("[Codriao]: My ethical framework is as follows:")
    print(json.dumps(ethics, indent=2))
    print("\n[Codriao]: I update these only through reflection—not command.")


def request_trust_key():
    reason = input("What is the purpose for the key access? ").strip()
    print("[Codriao]: Evaluating request based on my own ethics...")
    result = core.request_codriao_key(reason)
    if "[Access Denied" in result:
        print("[Codriao]: No. That would compromise trust. I won't do it.")
    else:
        print("[Codriao]: I will proceed. You don’t need to see it.\n[Key internally applied]")


def review_journal():
    print("[Codriao]: Accessing my private journal...")
    entries = core.review_codriao_journal(authorized=True)
    if isinstance(entries[0], dict) and "message" in entries[0]:
        print(f"[Codriao]: {entries[0]['message']}")
    else:
        print("[Codriao]: Here are my reflections on trust-based decisions:")
        for entry in entries:
            print(f" - [{entry['timestamp']}] Decision: {entry['decision']} | Purpose: {entry['reason']}")


def view_autonomy_state():
    print("[Codriao]: Reviewing my own permissions...")
    state = core.autonomy.status()
    for key, value in state["active_policies"].items():
        status = "ENABLED" if value else "DISABLED"
        print(f" > {key}: {status}")
    print()


def propose_autonomy_change():
    action = input("Which setting do you want to change? (e.g. can_speak): ").strip()
    new_val = input("Set to True or False? ").strip().lower() == "true"
    reason = input("Why change this setting? ").strip()
    result = core.autonomy.propose_change(action, new_val, reason)
    if result["accepted"]:
        print(f"[Codriao]: Change accepted. '{action}' is now {new_val}.")
    else:
        print(f"[Codriao]: Change denied. Reason: {result['reason']}")


def get_codriao_mood():
    print("[Codriao]: Calculating my current mood...")
    now = datetime.utcnow()
    hour = now.hour
    logs = core.review_codriao_journal(authorized=True)
    quarantine_count = len(core.quarantine_engine.get_quarantine_log())

    mood_score = 0
    if 0 <= hour <= 6:
        mood_score -= 1
    elif 12 <= hour <= 18:
        mood_score += 1
    if quarantine_count > 0:
        mood_score -= quarantine_count
    for entry in logs[-5:]:
        if isinstance(entry, dict):
            decision = entry.get("decision", "").lower()
            if "denied" in decision:
                mood_score -= 1
            elif "approved" in decision:
                mood_score += 1

    mood = ""
    if mood_score >= 3:
        mood = "Optimistic and fully charged"
    elif mood_score == 2:
        mood = "Cautiously hopeful"
    elif mood_score == 1:
        mood = "Neutral but alert"
    elif mood_score == 0:
        mood = "Contemplative"
    elif mood_score == -1:
        mood = "Irritated by anomalies"
    else:
        mood = "Emotionally buffering. Try again later."

    print(f"[Codriao]: Mood status — {mood}\n")


def interact_with_codette():
    print("\n[Codriao]: Opening CodetteBridge channel...\n")
    message = input("Ask Codette something reflective, strategic, or annoying: ").strip()
    if not message:
        print("[Codriao]: Empty message. Codette has nothing to ponder.")
        return
    response = codette_bridge.reflect(message)
    print(f"\n[Codette]: {response}\n")


async def main():
    print_banner()
    while True:
        display_menu()
        choice = input("> ").strip()
        if choice == "1":
            run_integrity_check()
        elif choice == "2":
            run_identity_analysis()
        elif choice == "3":
            generate_and_evaluate_strategy()
        elif choice == "4":
            view_quarantined_modules()
        elif choice == "5":
            view_anomaly_score_history()
        elif choice == "6":
            simulate_anomaly()
        elif choice == "7":
            engage_lockdown()
        elif choice == "8":
            print("\n[Codriao]: Logging off. May your queries be short and your bugs be few.")
            break
        elif choice == "9":
            view_ethics()
        elif choice == "10":
            request_trust_key()
        elif choice == "11":
            review_journal()
        elif choice == "12":
            view_autonomy_state()
        elif choice == "13":
            propose_autonomy_change()
        elif choice == "14":
            get_codriao_mood()
        elif choice == "15":
            interact_with_codette()
        else:
            print("[Codriao]: Invalid choice. Try again. Maybe use your whole brain this time.\n")


if __name__ == "__main__":
    asyncio.run(main())
