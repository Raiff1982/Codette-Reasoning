import os
import json
from datetime import datetime
import uuid

RESULTS_DIR = "results"

def save_result(data: dict) -> str:
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{unique_id}.json"
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }, f, indent=2)
    return filename

def load_result(filename: str) -> dict:
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        return {"error": "Result not found."}
    with open(path, "r") as f:
        return json.load(f)