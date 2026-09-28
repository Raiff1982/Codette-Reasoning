import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("codette.log"), logging.StreamHandler()]
)


def log_event(event_type: str, details: dict):
    timestamp = datetime.utcnow().isoformat()
    log_message = f"[{event_type}] {timestamp} - {details}"
    logging.info(log_message)
