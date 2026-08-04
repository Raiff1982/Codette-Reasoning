import librosa
import numpy as np
import logging
from tensorflow.keras.models import load_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TBAudioProcessor:
    """Processes real cough audio for TB detection"""

    def __init__(self, model_path="tb_cough_model.h5"):
        try:
            self.model = load_model(model_path)
            logger.info("TB Audio Processor Model Loaded Successfully.")
        except Exception as e:
            logger.error(f"Failed to load TB Audio Model: {e}")
            self.model = None

    def process_audio(self, audio_path):
        """Analyze cough audio and return TB risk assessment."""
        if not self.model:
            return {"error": "Model not loaded. Cannot process audio."}

        try:
            y, sr = librosa.load(audio_path, sr=16000)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
            mfccs = np.mean(mfccs.T, axis=0).reshape(1, -1)  # Flatten MFCCs

            prediction = self.model.predict(mfccs)
            confidence = float(prediction[0][0])
            result = "TB Detected" if confidence > 0.5 else "No TB"
            
            return {
                "result": result,
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"error": "Audio processing failed."}
