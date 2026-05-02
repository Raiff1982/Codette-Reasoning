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
        """LEGACY — writes a shallow cocoon with no v3 provenance fields.

        Production reasoning paths must use wrap_reasoning(v3_cocoon=...) instead.
        This method is retained only as the internal fallback inside wrap_reasoning()
        when no CocoonV3 instance is available, and for legacy symbolic/prompt wraps
        that are not inference outputs.

        If you are calling this directly from new code, stop and use wrap_reasoning()
        with a fully-built CocoonV3.
        """
        import logging as _log
        _log.getLogger(__name__).debug(
            "[CognitionCocooner] wrap() called — writing legacy shallow cocoon "
            "(no v3 provenance). Prefer wrap_reasoning(v3_cocoon=...) for inference paths."
        )
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
                       metadata: Optional[Dict] = None,
                       v3_cocoon=None) -> str:
        """
        Wrap a reasoning exchange as a cocoon and persist to disk.

        Args:
            query:     User query
            response:  AI response (truncated to 500 chars in legacy block)
            adapter:   Which adapter produced this
            metadata:  Optional shallow metadata dict (legacy path)
            v3_cocoon: Optional CocoonV3 instance — when provided, its full
                       serialized dict is embedded in the disk file, replacing
                       the legacy shallow metadata structure.  This is the
                       preferred path for all new forge writes.

        Returns:
            Cocoon ID (file stem)
        """
        if v3_cocoon is not None and hasattr(v3_cocoon, "to_dict"):
            # Full v3 path: embed complete provenance, metrics, integrity data
            v3_dict = v3_cocoon.to_dict()
            cocoon_id = f"cocoon_{int(v3_cocoon.timestamp)}_{random.randint(1000, 9999)}"
            disk_payload = {
                "type": "reasoning_v3",
                "id": cocoon_id,
                "timestamp": v3_cocoon.timestamp,
                "schema_version": v3_dict.get("serialization_version", "3.0"),
                "execution_path": v3_dict.get("execution_path", "unknown"),
                "model_inference_invoked": v3_dict.get("model_inference_invoked", False),
                "orchestrator_trace_id": v3_dict.get("orchestrator_trace_id", ""),
                "cocoon_integrity": v3_dict.get("cocoon_integrity", "partial"),
                "cocoon_integrity_score": v3_dict.get("cocoon_integrity_score", 0.0),
                "wrapped": {
                    "query": query,
                    "response": response[:2000],
                    "adapter": adapter,
                    "timestamp": v3_cocoon.timestamp,
                },
                "v3": v3_dict,
            }
            if metadata:
                disk_payload["wrapped"]["metadata"] = metadata
            file_path = self.storage_path / f"{cocoon_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(disk_payload, f, indent=2, ensure_ascii=False, default=str)
            return cocoon_id

        # Legacy path — shallow metadata only
        thought = {
            "query": query,
            "response": response[:500],
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

    def recall_relevant(self, query: str, max_results: int = 3,
                        min_overlap: int = 2) -> List[Dict]:
        """
        Recall reasoning cocoons relevant to a query using keyword overlap.

        Uses simple but effective keyword matching — counts how many significant
        words from the query appear in each stored cocoon's query/response.
        Returns top matches sorted by relevance.

        Args:
            query: Current user query to match against
            max_results: Maximum cocoons to return
            min_overlap: Minimum keyword overlap to qualify

        Returns:
            List of relevant reasoning cocoons with relevance scores
        """
        # Extract significant words from query (skip short/common words)
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "don",
            "now", "it", "its", "this", "that", "these", "those", "i",
            "me", "my", "we", "our", "you", "your", "he", "she", "they",
            "what", "which", "who", "whom", "and", "but", "or", "if",
            "about", "up", "down", "also", "really", "tell", "know",
        }
        query_words = set(
            w.lower().strip(".,!?;:\"'()[]{}") for w in query.split()
            if len(w) > 2 and w.lower() not in stop_words
        )

        if not query_words:
            return self.get_recent_reasoning(limit=max_results)

        scored = []
        for file in sorted(self.storage_path.glob("cocoon_*.json"),
                          key=lambda f: f.stat().st_mtime, reverse=True)[:200]:
            try:
                with open(file, "r") as f:
                    cocoon = json.load(f)
                if cocoon.get("type") != "reasoning":
                    continue

                wrapped = cocoon.get("wrapped", {})
                cocoon_text = (
                    str(wrapped.get("query", "")) + " " +
                    str(wrapped.get("response", ""))
                ).lower()

                # Count keyword overlap
                overlap = sum(1 for w in query_words if w in cocoon_text)
                if overlap >= min_overlap:
                    scored.append((overlap, wrapped))
            except Exception:
                continue

        # Sort by relevance (most overlap first)
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # No relevant matches — fall back to recent
            return self.get_recent_reasoning(limit=max_results)

        return [item[1] for item in scored[:max_results]]
