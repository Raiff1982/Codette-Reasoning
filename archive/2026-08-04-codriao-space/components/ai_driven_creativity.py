class AIDrivenCreativity:
    """Generates creative content such as art, music, and literature"""
    def __init__(self):
        self.creativity_engine = CreativityEngine()

    def generate_art(self, prompt: str) -> str:
        """Generate art based on a prompt"""
        return self.creativity_engine.create_art(prompt)

    def compose_music(self, prompt: str) -> str:
        """Compose music based on a prompt"""
        return self.creativity_engine.compose_music(prompt)

    def write_literature(self, prompt: str) -> str:
        """Write literature based on a prompt"""
        return self.creativity_engine.write_literature(prompt)