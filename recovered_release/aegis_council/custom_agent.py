from aegis_council import AegisAgent
from typing import Dict, Any

class CustomAgent(AegisAgent):
    def __init__(self, name: str, memory):
        super().__init__(name, memory)

    def analyze(self, input_data: Dict[str, Any]) -> None:
        try:
            text = input_data.get("text", "")
            self.result = {"custom_analysis": len(text.split())}
            self.explanation = f"CustomAgent counted {self.result['custom_analysis']} words in input."
            self.influence["word_count"] = self.result["custom_analysis"] / 100.0
            self.logger.info(self.explanation)
        except Exception as e:
            self.result = {"error": str(e)}
            self.explanation = f"CustomAgent failed: {e}"
            self.logger.error(self.explanation)

    def report(self) -> Dict[str, Any]:
        return {"result": self.result, "explanation": self.explanation}