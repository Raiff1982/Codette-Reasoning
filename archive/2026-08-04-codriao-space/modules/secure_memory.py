import base64
import json
from cryptography.fernet import Fernet

class SecureMemorySession:
    """Handles encryption/decryption for user vectors"""
    
    def __init__(self, key: bytes):
        self.key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))  # Fernet key must be 32 bytes
        self.fernet = Fernet(self.key)
        self.memory_store = {}

    def encrypt_vector(self, user_id, vector):
        """Encrypts and stores vector under user ID"""
        if user_id not in self.memory_store:
            self.memory_store[user_id] = []
        serialized = json.dumps(vector.tolist()).encode()
        encrypted = self.fernet.encrypt(serialized)
        self.memory_store[user_id].append(encrypted)

    def decrypt_vectors(self, user_id):
        """Decrypts and returns all stored vectors for a user"""
        if user_id not in self.memory_store:
            return []
        decrypted = []
        for enc in self.memory_store[user_id]:
            try:
                raw = self.fernet.decrypt(enc)
                array = json.loads(raw.decode())
                decrypted.append(array)
            except Exception:
                continue
        return decrypted