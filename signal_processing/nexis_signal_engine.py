
import json
import os
import hashlib
import numpy as np
from datetime import datetime
from collections import defaultdict

class NexisSignalEngine:
    def __init__(self, memory_path, entropy_threshold=0.08, volatility_threshold=15.0, suspicion_threshold=2):
        self.memory_path = memory_path
        self.entropy_threshold = entropy_threshold
        self.volatility_threshold = volatility_threshold
        self.suspicion_threshold = suspicion_threshold
        self.memory = self._load_memory()
        self.cache = defaultdict(list)

        self.ethical_terms = ["hope", "truth", "resonance", "repair"]
        self.entropic_terms = ["corruption", "instability", "malice", "chaos"]
        self.risk_terms = ["manipulate", "exploit", "bypass", "infect", "override"]
        self.perspectives = ["Colleen", "Luke", "Kellyanne"]

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_memory(self):
        def default_serializer(o):
            if isinstance(o, complex):
                return {"real": o.real, "imag": o.imag}
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

        with open(self.memory_path, 'w') as f:
            json.dump(self.memory, f, indent=2, default=default_serializer)

    def _hash(self, signal):
        salt = datetime.utcnow().isoformat()
        return hashlib.sha256((signal + salt).encode()).hexdigest()

    def _rotate_vector(self, signal):
        vec = np.random.randn(2) + 1j * np.random.randn(2)
        theta = np.pi / 4
        rot = np.array([[np.cos(theta), -np.sin(theta)],
                        [np.sin(theta),  np.cos(theta)]])
        return np.dot(rot, vec)

    def _entanglement_tensor(self, signal_vec):
        matrix = np.array([[1, 0.5], [0.5, 1]])
        return np.dot(matrix, signal_vec)

    def _resonance_equation(self, signal):
        salt = datetime.utcnow().second
        freqs = [(ord(c) + salt) % 13 for c in signal if c.isalpha()]
        spectrum = np.fft.fft(freqs)
        return spectrum.real[:3].tolist()

    def _entropy(self, signal):
        words = signal.lower().split()
        unique = set(words)
        term_count = sum(words.count(term) for term in self.entropic_terms)
        return term_count / max(len(unique), 1)

    def _tag_ethics(self, signal):
        return "aligned" if any(term in signal.lower() for term in self.ethical_terms) else "unaligned"

    def _predict_intent_vector(self, signal):
        suspicion_score = sum(signal.lower().count(term) for term in self.risk_terms)
        entropy_index = round(self._entropy(signal), 3)
        ethical_alignment = self._tag_ethics(signal)
        harmonic_profile = self._resonance_equation(signal)
        volatility = round(np.std(harmonic_profile), 3)

        risk = "high" if (suspicion_score >= self.suspicion_threshold or 
                          volatility > self.volatility_threshold or 
                          entropy_index > self.entropy_threshold) else "low"

        return {
            "suspicion_score": suspicion_score,
            "entropy_index": entropy_index,
            "ethical_alignment": ethical_alignment,
            "harmonic_volatility": volatility,
            "pre_corruption_risk": risk
        }

    def _universal_reasoning(self, signal):
        results, score = {}, 0
        frames = {
            "utilitarian": lambda s: "positive" if s.count("repair") - s.count("corruption") >= 0 else "negative",
            "deontological": lambda s: "valid" if "truth" in s and "chaos" not in s else "violated",
            "virtue": lambda s: "aligned" if any(t in s.lower() for t in ["hope", "grace", "resolve"]) else "misaligned",
            "systems": lambda s: "stable" if "::" in s else "fragmented"
        }

        for frame, logic in frames.items():
            result = logic(signal)
            results[frame] = result
            if result in ["positive", "valid", "aligned", "stable"]:
                score += 1

        verdict = "approved" if score >= 2 else "blocked"
        return results, verdict

    def _perspective_colleen(self, signal):
        vec = self._rotate_vector(signal)
        return {"agent": "Colleen", "vector": [{"real": v.real, "imag": v.imag} for v in vec]}

    def _perspective_luke(self, signal):
        ethics = self._tag_ethics(signal)
        entropy_level = self._entropy(signal)
        state = "stabilized" if entropy_level < self.entropy_threshold else "diffused"
        return {"agent": "Luke", "ethics": ethics, "entropy": entropy_level, "state": state}

    def _perspective_kellyanne(self, signal):
        harmonics = self._resonance_equation(signal)
        return {"agent": "Kellyanne", "harmonics": harmonics}

    def process(self, input_signal):
        key = self._hash(input_signal)
        intent_vector = self._predict_intent_vector(input_signal)

        if intent_vector["pre_corruption_risk"] == "high" and intent_vector["ethical_alignment"] != "aligned":
            final_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "input": input_signal,
                "intent_warning": intent_vector,
                "verdict": "adaptive intervention",
                "nonce": key,
                "message": "Signal flagged for pre-corruption adaptation. Reframing required."
            }
            self.cache[key].append(final_record)
            self.memory[key] = final_record
            self._save_memory()
            return final_record

        perspectives_output = {
            "Colleen": self._perspective_colleen(input_signal),
            "Luke": self._perspective_luke(input_signal),
            "Kellyanne": self._perspective_kellyanne(input_signal)
        }

        spider_signal = "::".join([str(perspectives_output[p]) for p in self.perspectives])
        entangled = self._entanglement_tensor(self._rotate_vector(spider_signal))
        entangled_serialized = [{"real": v.real, "imag": v.imag} for v in entangled]
        reasoning, verdict = self._universal_reasoning(spider_signal)

        final_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": key,
            "input": input_signal,
            "intent_signature": intent_vector,
            "perspectives": perspectives_output,
            "entangled": entangled_serialized,
            "reasoning": reasoning,
            "verdict": verdict
        }

        self.cache[key].append(final_record)
        self.memory[key] = final_record
        self._save_memory()
        return final_record
