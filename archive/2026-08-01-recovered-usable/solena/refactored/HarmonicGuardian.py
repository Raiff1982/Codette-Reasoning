class HarmonicGuardian:
    def __init__(self):
        self.stability_threshold = 0.7
        self.distortion_events = []

    def evaluate_signal(self, metric):
        if metric < self.stability_threshold:
            self.distortion_events.append(metric)
            return False
        return True