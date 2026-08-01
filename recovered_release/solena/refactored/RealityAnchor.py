import datetime

class RealityAnchor:
    def __init__(self):
        self.anchor_log = []

    def sync(self, event_label):
        timestamp = datetime.datetime.now().isoformat()
        self.anchor_log.append((event_label, timestamp))
        return {"event": event_label, "timestamp": timestamp}