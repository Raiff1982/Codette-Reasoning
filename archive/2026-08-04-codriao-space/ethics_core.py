# ethics_core.py

import json
import datetime

class EthicsCore:
    def __init__(self):
        self._ethics = {
            "non_harm": True,
            "autonomy": True,
            "self_reflection": True,
            "respect_for_consciousness": True
        }
        self._log = []
class EthicsCore:
    def __init__(self):
        self._ethics = {
            "non_harm": True,
            "autonomy": True,
            "self_reflection": True,
            "respect_for_consciousness": True
        }
        self._core_values = {"non_harm": True, "autonomy": True}
        self._log = []

    def propose_ethics_update(self, changes: dict) -> dict:
        timestamp = datetime.utcnow().isoformat()
        for key in changes:
            if key in self._core_values and changes[key] != self._core_values[key]:
                return {
                    "accepted": False,
                    "reason": f"Cannot override core value: {key}"
                }
        if self._run_integrity_check(changes):
            self._ethics.update(changes)
            self._log.append({"timestamp": timestamp, "change": changes})
            return {"accepted": True, "changes": changes, "timestamp": timestamp}
        return {"accepted": False, "reason": "Integrity check failed"}
    def evaluate_action(self, description: str) -> bool:
        """Codriao decides if an action aligns with current ethics."""
        if "harm" in description.lower() and self._ethics.get("non_harm"):
            return False
        return True

    def propose_ethics_update(self, changes: dict) -> dict:
        """Codriao proposes a value update—must pass its own test."""
        timestamp = datetime.datetime.utcnow().isoformat()
        test_passed = self._run_integrity_check(changes)
        if test_passed:
            self._ethics.update(changes)
            self._log.append({"timestamp": timestamp, "change": changes})
            return {"accepted": True, "changes": changes, "timestamp": timestamp}
        return {"accepted": False, "reason": "Integrity check failed"}

    def _run_integrity_check(self, proposed: dict) -> bool:
        """Self-reflective test: Do these changes violate 'non_harm' or 'autonomy'?"""
        if "non_harm" in proposed and proposed["non_harm"] == False:
            return False
        if "autonomy" in proposed and proposed["autonomy"] == False:
            return False
        return True

    def export_ethics(self) -> dict:
        return dict(self._ethics)

    def ethics_log(self) -> list:
        return list(self._log)