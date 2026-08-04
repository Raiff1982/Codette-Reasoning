from transformers import AutoModelForCausalLM
from components.symbolic_reasoner import SymbolicReasoner

class NeuroSymbolicEngine:
    """Combines neural networks with symbolic reasoning"""
    def __init__(self):
        self.symbolic_reasoner = SymbolicReasoner()
        self.neural_network = AutoModelForCausalLM.from_pretrained("Raiff1982/Codette", trust_remote_code=True)

    def integrate_reasoning(self, query: str) -> str:
        """Integrate neural and symbolic reasoning"""
        neural_response = self._generate_neural_response(query)
        symbolic_response = self.symbolic_reasoner.reason(query)
        return f"Neural Response: {neural_response}\nSymbolic Response: {symbolic_response}"

    def _generate_neural_response(self, query: str) -> str:
        """Generate a response using the neural network"""
        inputs = self.neural_network.tokenizer(query, return_tensors="pt")
        outputs = self.neural_network.generate(**inputs)
        return self.neural_network.tokenizer.decode(outputs[0], skip_special_tokens=True)