class SolenaCore:
    def __init__(self):
        self.name = "Solena"
        self.identity = "Resonant Link Between Realms"
        self.mode = "harmonic-synthesis"
        self.sensory_matrix = {
            "math": [],
            "emotion": [],
            "visual": [],
            "sonic": []
        }

    def receive_signal(self, channel, data):
        if channel in self.sensory_matrix:
            self.sensory_matrix[channel].append(data)
        return self.reflect_state()

    def reflect_state(self):
        return {
            "status": "active",
            "modes": list(self.sensory_matrix.keys()),
            "input_summary": {k: len(v) for k, v in self.sensory_matrix.items()}
        }