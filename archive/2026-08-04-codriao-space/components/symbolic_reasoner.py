import logging
import datetime
from typing import Dict, List, Union


class SymbolicReasoner:
    """
    A symbolic logic engine for managing rules, facts, and inference.
    Supports basic forward chaining, contradiction checks, and assertions.
    """

    def __init__(self):
        self.facts: Dict[str, bool] = {}
        self.rules: List[Dict[str, Union[List[str], str]]] = []
        self.inference_log: List[Dict] = []
        logging.info("[SymbolicReasoner] Initialized.")

    def add_fact(self, statement: str, value: bool = True):
        if statement in self.facts and self.facts[statement] != value:
            logging.warning(f"[SymbolicReasoner] Contradiction detected: {statement}")
            raise ValueError(f"Contradiction: {statement} already known as {self.facts[statement]}")
        self.facts[statement] = value
        logging.info(f"[SymbolicReasoner] Fact added: {statement} = {value}")
        self._evaluate_rules()

    def add_rule(self, premises: List[str], conclusion: str):
        rule = {"if": premises, "then": conclusion}
        self.rules.append(rule)
        logging.info(f"[SymbolicReasoner] Rule added: IF {premises} THEN {conclusion}")
        self._evaluate_rules()

    def _evaluate_rules(self):
        inferred = True
        while inferred:
            inferred = False
            for rule in self.rules:
                if all(self.facts.get(prem, False) for prem in rule["if"]):
                    conclusion = rule["then"]
                    if conclusion not in self.facts:
                        self.facts[conclusion] = True
                        self.inference_log.append({
                            "inferred": conclusion,
                            "based_on": rule["if"],
                            "timestamp": datetime.datetime.utcnow().isoformat()
                        })
                        logging.info(f"[SymbolicReasoner] Inferred: {conclusion} from {rule['if']}")
                        inferred = True

    def query(self, statement: str) -> bool:
        result = self.facts.get(statement, False)
        logging.info(f"[SymbolicReasoner] Query: {statement} = {result}")
        return result

    def explain(self, statement: str) -> List[Dict]:
        return [entry for entry in self.inference_log if entry["inferred"] == statement]

    def status(self):
        return {
            "facts": self.facts,
            "rules": self.rules,
            "inference_log": self.inference_log
        }