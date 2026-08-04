import asyncio
import logging
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from CodriaoCore import CodriaoCore
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)  # Ensure base directory is included
sys.path.append(os.path.join(BASE_DIR, "modules"))  # Ensure 'modules/' is included

try:
    from tb_image_processor import TBImageProcessor
    from tb_audio_processor import TBAudioProcessor
except ModuleNotFoundError:
    try:
        from modules.tb_image_processor import TBImageProcessor
        from modules.tb_audio_processor import TBAudioProcessor
    except ModuleNotFoundError:
        raise ImportError("❌ Could not locate tb_image_processor.py or tb_audio_processor.py. Ensure they are in the root directory or inside 'modules/'.")
        
class CodriaoHealthModule:
    """Embedded compassionate TB detection within Codriao's architecture"""

    def __init__(self, ai_core: "CodriaoCore"):
        self.ai_core = ai_core
        self.image_processor = TBImageProcessor()
        self.audio_processor = TBAudioProcessor()

    async def evaluate_tb_risk(self, image_path: str, audio_path: str, user_id: int):
        image_result, image_confidence = self.image_processor.process_image(image_path)
        audio_result, audio_confidence = self.audio_processor.process_audio(audio_path)

        if "Error" in [image_result, audio_result]:
            tb_risk = "UNKNOWN"
        elif image_result == "TB Detected" and audio_result == "TB Detected":
            tb_risk = "HIGH"
        elif image_result == "TB Detected" or audio_result == "TB Detected":
            tb_risk = "MEDIUM"
        else:
            tb_risk = "LOW"

        combined_query = (
            f"Medical Analysis Input: TB image: {image_result} (confidence {image_confidence:.2f}), "
            f"Audio: {audio_result} (confidence {audio_confidence:.2f}). Risk Level: {tb_risk}. "
            f"Please respond with a kind, ethical interpretation and recommended next steps."
        )

        response = await self.ai_core.generate_response(combined_query, user_id)

        return {
    "tb_risk": tb_risk,
    "image_analysis": {"result": image_result, "confidence": image_confidence},
    "audio_analysis": {"result": audio_result, "confidence": audio_confidence},
    "ethical_analysis": response.get("response"),
    "explanation": response.get("explanation"),
    "system_health": response.get("health")
}
        