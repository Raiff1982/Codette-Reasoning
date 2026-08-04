class ExplainableAI:
    """Provides transparency in AI decision-making"""
    def __init__(self):
        self.explanations = []

    def explain_decision(self, decision: str, context: str) -> str:
        """Explain the AI's decision-making process"""
        explanation = f"Decision: {decision}\nContext: {context}\nReasoning: {self._generate_reasoning(context)}"
        self.explanations.append(explanation)
        return explanation

    def _generate_reasoning(self, context: str) -> str:
        """Generate reasoning for the decision"""
        return f"The decision was made based on the following context: {context}"