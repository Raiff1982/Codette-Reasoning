import importlib.util
from pathlib import Path
import logging

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_secure_memory_module(temp_path="./modules/secure_memory.py"):
    """
    Dynamically loads secure_memory.py from a specified path.
    Returns the module object if successful.
    """
    # Validate the file path
    secure_memory = Path(temp_path)
    if not secure_memory.exists():
        logging.error(f"File not found at specified path: {temp_path}")
        raise FileNotFoundError(f"File not found: {temp_path}")

    # Log the loading process
    logging.info(f"Loading secure_memory module from: {temp_path}")

    try:
        # Create a module specification and load it dynamically
        spec = importlib.util.spec_from_file_location("secure_memory", temp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Log success and return the module
        logging.info("secure_memory module successfully loaded.")
        return module
    except Exception as e:
        logging.error(f"Failed to load secure_memory module: {e}")
        raise RuntimeError(f"Error while loading secure_memory module: {e}")
