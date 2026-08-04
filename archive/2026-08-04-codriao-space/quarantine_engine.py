# quarantine_engine.py

import logging

class QuarantineEngine:
    def __init__(self):
        self.quarantined_modules = []

    def quarantine(self, module_name: str, reason: str):
        if module_name not in self.quarantined_modules:
            self.quarantined_modules.append(module_name)
            logging.warning(f"[Quarantine] Module '{module_name}' quarantined: {reason}")

    def is_quarantined(self, module_name: str) -> bool:
        return module_name in self.quarantined_modules

    def get_quarantine_log(self):
        return self.quarantined_modules