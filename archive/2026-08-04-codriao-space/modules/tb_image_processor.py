import os
import cv2
import numpy as np
import logging
from tensorflow.keras.models import load_model

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TBImageProcessor:
    """Processes TB images using a trained CNN model for risk assessment."""

    def __init__(self, model_path="tb_cnn_model.h5"):
        # Validate model path
        if not os.path.exists(model_path):
            logger.error(f"Model path '{model_path}' does not exist. Please check the path.")
            self.model = None
            return

        try:
            self.model = load_model(model_path)
            logger.info("TB Image Processor model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load the TB Image Model: {e}")
            self.model = None

    def process_image(self, image_path):
        """Analyze a TB image and return risk assessment."""
        # Validate the image file
        if not os.path.exists(image_path):
            logger.error(f"Image path '{image_path}' does not exist.")
            return {"error": "Image file not found."}
        
        if self.model is None:
            logger.error("Model is not loaded. Cannot process the image.")
            return {"error": "Model not loaded."}

        try:
            # Load and preprocess image
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                logger.error(f"Failed to read the image at path '{image_path}'.")
                return {"error": "Invalid image format or corrupted file."}

            # Resize for CNN input and normalize
            if image.shape[0] < 128 or image.shape[1] < 128:
                logger.warning("Image dimensions are smaller than expected, resizing may affect accuracy.")
            image = cv2.resize(image, (128, 128))
            image = np.expand_dims(image, axis=[0, -1]) / 255.0

            # Make prediction
            prediction = self.model.predict(image)
            confidence = float(prediction[0][0])
            result = "TB Detected" if confidence > 0.5 else "No TB"

            logger.info(f"Prediction result: {result}, Confidence: {confidence:.2f}")
            return {
                "result": result,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"Error during image processing: {e}")
            return {"error": f"Failed to process image: {str(e)}"}

# Example usage
if __name__ == "__main__":
    # Specify the model and image paths
    model_path = "path/to/your/tb_cnn_model.h5"
    image_path = "path/to/your/tb_image.jpg"

    # Instantiate the processor and analyze the image
    processor = TBImageProcessor(model_path=model_path)
    result = processor.process_image(image_path=image_path)

    # Log or print the final result
    if "error" in result:
        logger.error(f"Processing failed: {result['error']}")
    else:
        logger.info(f"Final Result: {result['result']}, Confidence: {result['confidence']:.2f}")