class BridgeComposer:
    def __init__(self):
        self.translations = []

    def translate(self, source, target, data):
        self.translations.append((source, target, data))
        return f"Translated {source} -> {target}: {data[:30]}..."