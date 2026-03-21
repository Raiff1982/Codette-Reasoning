"""
CognitionCocooner - Thought Encapsulation Module
=================================================

Ported from J:\TheAI\src\framework\cognition_cocooner.py
Original design by Jonathan Harrison (Raiffs Bits LLC)

Wraps active thoughts as persistable "cocoons" with optional AES encryption.
Integrates with LivingMemoryKernel to store reasoning outputs as recoverable
memory anchors.
"""

import json
import os
import time
import random
from typing import Union, Dict, Any, List, Optional
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class CognitionCocooner:
    """
    Encapsulates active "thoughts" as persistable "cocoons".

    Supports:
    - Plain text wrapping (prompts, functions, symbols)
    - AES-256 encryption for sensitive thoughts
    - Persistent storage on disk
    - Integration with LivingMemoryKernel for recall
    """

    def __init__(self, storage_path: str = "cocoons", encryption_key: bytes = None):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        if ENCRYPTION_AVAILABLE and encryption_key:
            self.key = encryption_key
            self.fernet = Fernet(self.key)
        elif ENCRYPTION_AVAILABLE:
            self.key = Fernet.generate_key()
            self.fernet = Fernet(self.key)
        else:
            self.key = None
            self.fernet = None

    def wrap(self, thought: Dict[str, Any], type_: str = "prompt") -> str:
        """
        Wrap a thought as a cocoon and save to disk.

        Args:
            thought: Thought content (dict)
            type_: Cocoon type ("prompt", "function", "symbolic", "reasoning")

        Returns:
            Cocoon ID for later retrieval
        """
        cocoon_id = f"cocoon_{int(time.time())}_{random.randint(1000,9999)}"
        cocoon = {
            "type": type_,
            "id": cocoon_id,
            "timestamp": time.time(),
            "wrapped": self._generate_wrapper(thought, type_)
        }
        file_path = self.storage_path / f"{cocoon_id}.json"

        with open(file_path, "w") as f:
            json.dump(cocoon, f, indent=2)

        return cocoon_id

    def unwrap(self, cocoon_id: str) -> Union[str, Dict[str, Any]]:
        """Unwrap a cocoon by ID."""
        file_path = self.storage_path / f"{cocoon_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Cocoon {cocoon_id} not found.")

        with open(file_path, "r") as f:
            cocoon = json.load(f)

        return cocoon["wrapped"]

    def wrap_encrypted(self, thought: Dict[str, Any]) -> str:
        """Wrap and encrypt a thought (requires cryptography package)."""
        if not ENCRYPTION_AVAILABLE or not self.fernet:
            raise RuntimeError("Encryption not available - install cryptography package")

        encrypted = self.fernet.encrypt(json.dumps(thought).encode()).decode()
        cocoon_id = f"cocoon_{int(time.time())}_{random.randint(10000,99999)}"
        cocoon = {
            "type": "encrypted",
            "id": cocoon_id,
            "timestamp": time.time(),
            "wrapped": encrypted
        }
        file_path = self.storage_path / f"{cocoon_id}.json"

        with open(file_path, "w") as f:
            json.dump(cocoon, f, indent=2)

        return cocoon_id

    def unwrap_encrypted(self, cocoon_id: str) -> Dict[str, Any]:
        """Unwrap and decrypt a cocoon."""
        if not ENCRYPTION_AVAILABLE or not self.fernet:
            raise RuntimeError("Encryption not available - install cryptography package")

        file_path = self.storage_path / f"{cocoon_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Cocoon {cocoon_id} not found.")

        with open(file_path, "r") as f:
            cocoon = json.load(f)

        decrypted = self.fernet.decrypt(cocoon["wrapped"].encode()).decode()
        return json.loads(decrypted)

    def wrap_reasoning(self, query: str, response: str, adapter: str = "unknown",
                       metadata: Optional[Dict] = None) -> str:
        """
        Wrap a reasoning exchange (query + response) as a cocoon.
        This is the primary integration point with ForgeEngine.

        Args:
            query: User query
            response: AI response
            adapter: Which adapter produced this
            metadata: Optional extra metadata (complexity, domain, etc.)

        Returns:
            Cocoon ID
        """
        thought = {
            "query": query,
            "response": response[:500],  # Truncate to prevent bloat
            "adapter": adapter,
            "timestamp": time.time(),
        }
        if metadata:
            thought["metadata"] = metadata

        return self.wrap(thought, type_="reasoning")

    def wrap_and_store(self, content: str, type_: str = "prompt") -> str:
        """Convenience method to wrap and store string content."""
        thought = {"content": content, "timestamp": time.time()}
        return self.wrap(thought, type_)

    def _generate_wrapper(self, thought: Dict[str, Any], type_: str) -> Union[str, Dict[str, Any]]:
        """Generate type-specific wrapper for thought."""
        if type_ == "prompt":
            return f"What does this mean in context? {thought}"
        elif type_ == "function":
            return f"def analyze(): return {thought}"
        elif type_ == "symbolic":
            return {k: round(v, 2) if isinstance(v, (int, float)) else v
                   for k, v in thought.items()}
        elif type_ == "reasoning":
            return thought  # Store as-is for reasoning exchanges
        else:
            return thought

    def list_cocoons(self) -> List[str]:
        """List all cocoon IDs."""
        return [f.stem for f in self.storage_path.glob("cocoon_*.json")]

    def delete_cocoon(self, cocoon_id: str) -> bool:
        """Delete a cocoon by ID."""
        file_path = self.storage_path / f"{cocoon_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_recent_reasoning(self, limit: int = 5) -> List[Dict]:
        """
        Get recent reasoning cocoons for context enrichment.

        Returns:
            List of recent reasoning exchange dicts
        """
        reasoning_cocoons = []
        for file in sorted(self.storage_path.glob("cocoon_*.json"),
                          key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                with open(file, "r") as f:
                    cocoon = json.load(f)
                if cocoon.get("type") == "reasoning":
                    reasoning_cocoons.append(cocoon["wrapped"])
                    if len(reasoning_cocoons) >= limit:
                        break
            except Exception:
                continue

        return reasoning_cocoons
