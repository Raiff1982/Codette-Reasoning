import tempfile
import os

# Your memory session code as a string
memory_isolation_code = """
from cryptography.fernet import Fernet
import numpy as np
import base64

class SecureMemorySession:
    def __init__(self, encryption_key: bytes = None):
        self.key = encryption_key or Fernet.generate_key()
        self.fernet = Fernet(self.key)
        self.sessions = {}

    def encrypt_vector(self, user_id: int, vector: np.ndarray) -> str:
        vector_bytes = vector.tobytes()
        encrypted = self.fernet.encrypt(vector_bytes)
        encoded = base64.b64encode(encrypted).decode('utf-8')
        self.sessions.setdefault(user_id, []).append(encoded)
        return encoded

    def decrypt_vectors(self, user_id: int) -> list:
        if user_id not in self.sessions:
            return []
        decrypted_vectors = []
        for encoded in self.sessions[user_id]:
            encrypted = base64.b64decode(encoded)
            decrypted = self.fernet.decrypt(encrypted)
            vector = np.frombuffer(decrypted, dtype=np.int64)
            decrypted_vectors.append(vector)
        return decrypted_vectors

    def get_encryption_key(self) -> bytes:
        return self.key
"""

def create_secure_memory_module():
    # Create a temporary file that acts as our secure_memory module
    with tempfile.NamedTemporaryFile("w+", suffix="_secure_memory.py", delete=False) as tmp:
        tmp.write(memory_isolation_code)
        tmp_path = tmp.name

    # Insert the temp file directory into sys.path so it can be imported
    import sys
    module_dir = os.path.dirname(tmp_path)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    return os.path.basename(tmp_path).replace(".py", "")
