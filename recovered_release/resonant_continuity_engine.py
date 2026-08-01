# Resonant Continuity Engine v0.1 - Laughing Logic
import numpy as np
import math
import time

class ResonantContinuityEngine:
    def __init__(self):
        self.emotion = 0.5
        self.energy = 1.0
        self.intent = 0.7
        self.midi_freq = 440.0
        self.darkness = 0.1
        self.speed = 1.0
        self.gravity = 1.2
        self.delta_matter = 0.01
        self.time_index = 0
        self.history = []

    def update_parameters(self):
        self.time_index += 1
        self.emotion = np.clip(np.sin(self.time_index / 40.0), -1, 1)
        self.intent = np.clip(np.cos(self.time_index / 50.0), -1, 1)
        self.midi_freq = 440 * 2 ** ((np.random.randint(60, 80) - 69) / 12)
        self.darkness = abs(np.sin(self.time_index / 60.0))
        self.delta_matter = np.random.normal(0.01, 0.005)

    def calculate_psi(self):
        t = self.time_index
        numerator = self.emotion * self.energy * self.midi_freq * self.intent
        denominator = (1 + abs(self.darkness)) * self.speed
        sine_wave = math.sin((2 * math.pi * t) / self.gravity)
        psi = (numerator / denominator) * sine_wave + self.delta_matter
        return psi

    def run(self, cycles=25):
        for _ in range(cycles):
            self.update_parameters()
            psi_r = self.calculate_psi()
            self.history.append({
                "time": self.time_index,
                "psi_r": psi_r,
                "emotion": self.emotion,
                "intent": self.intent,
                "midi_freq": self.midi_freq
            })
            if abs(psi_r) < 0.1:
                print(f"[Cycle {self.time_index}] Low resonance detected. EntropyJester says: 'Time to dance!'")
            elif psi_r > 1000:
                print(f"[Cycle {self.time_index}] ⚠️ Max psi resonance hit! Initiating harmonic laughter mode.")
            else:
                print(f"[Cycle {self.time_index}] Ψ_r = {psi_r:.4f} | 🎵 {int(self.midi_freq)}Hz | 💡 intent = {self.intent:.2f}")
            time.sleep(0.05)
        return self.history
