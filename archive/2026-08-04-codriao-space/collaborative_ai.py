class CollaborativeAI:
    """Enables collaboration with other AI systems and human experts"""
    def __init__(self):
        self.collaborators = []

    def add_collaborator(self, collaborator: Any):
        """Add a collaborator to the AI system"""
        self.collaborators.append(collaborator)

    def collaborate(self, query: str) -> str:
        """Collaborate with other AI systems and human experts"""
        responses = [collaborator.respond(query) for collaborator in self.collaborators]
        return "\n".join(responses)