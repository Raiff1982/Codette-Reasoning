"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""


import time
class MemoryItem:
    """
    Represents a single memory with content and an associated emotion.
    Attributes:
        content (str): The actual memory content or description.
        emotion_tag (str): Label for the emotion associated with this memory (e.g. "happy", "sad").
        intensity (float): Importance or strength of the memory (default 1.0, higher means more salient).
        valence (float): Numeric emotional valence derived from the emotion_tag (positive for pleasant emotions,
                         negative for unpleasant ones, range roughly -1.0 to 1.0).
        timestamp (float): Time when the memory was created (for recency tracking).
    """
    # Mapping from common emotion tags to a valence value (this can be expanded or refined)
    EMOTION_VALENCES = {
        "happy": 0.8, "joy": 0.8, "excited": 0.7, "love": 0.9,
        "sad": -0.8, "fear": -0.9, "angry": -0.7, "anger": -0.7, "anxious": -0.4,
        "neutral": 0.0, "positive": 0.5, "negative": -0.5
    }
    def __init__(self, content: str, emotion_tag: str, intensity: float = 1.0):
        self.content = content
        self.emotion_tag = emotion_tag
        self.intensity = intensity
        # Determine the valence from the tag, defaulting to 0.0 if unknown tag
        if emotion_tag in MemoryItem.EMOTION_VALENCES:
            self.valence = MemoryItem.EMOTION_VALENCES[emotion_tag]
        else:
            # If the emotion tag is not recognized, assume neutral valence (0.0)
            self.valence = 0.0
        # Store creation time (epoch seconds) for potential use in recency-based retrieval
        self.timestamp = time.time()
    def __repr__(self):
        return f"MemoryItem(content={self.content!r}, emotion={self.emotion_tag!r}, " \
               f"intensity={self.intensity:.2f}, valence={self.valence:.2f})"
class MemoryCocoon:
    """
    Container for an agent's memories. Provides methods to store new memories and retrieve them by emotion.
    Internally maintains an index for quick lookup of memories by emotion tag.
    """
    def __init__(self):
        # List of all MemoryItem objects
        self.memories = []
        # Index: emotion tag -> list of MemoryItems with that tag
        self.index_by_emotion = {}
    def add_memory(self, content: str, emotion_tag: str, intensity: float = 1.0) -> MemoryItem:
        """
        Create a new MemoryItem and add it to the cocoon.
        Updates the index_by_emotion for the memory's emotion tag.
        Returns the MemoryItem created.
        """
        memory = MemoryItem(content, emotion_tag, intensity)
        self.memories.append(memory)
        # Update index
        self.index_by_emotion.setdefault(emotion_tag, []).append(memory)
        return memory
    def get_memories_by_emotion(self, emotion_tag: str):
        """
        Retrieve all memories that have the given emotion tag.
        Returns a list of MemoryItems sorted by descending intensity.
        """
        memories = self.index_by_emotion.get(emotion_tag, [])
        # Sort by intensity (high to low) so that more intense memories come first
        return sorted(memories, key=lambda m: m.intensity, reverse=True)
    def get_recent_memories(self, n: int = 5):
        """
        Retrieve the n most recent memories added to the cocoon.
        Returns a list of MemoryItems sorted by recency (newest first).
        """
        return sorted(self.memories, key=lambda m: m.timestamp, reverse=True)[:n]
    def find_best_match(self, emotion_tag: str = None, emotion_valence: float = None) -> MemoryItem:
        """
        Find a memory that best matches the given emotional context.
        - If emotion_tag is provided and there are memories with that tag, return the highest-intensity one.
        - Otherwise, if emotion_valence is provided, return the memory with closest valence to that value (ties broken by intensity).
        - Returns None if no memories exist.
        """
        if emotion_tag:
            # Try exact tag match first
            tagged_mems = self.get_memories_by_emotion(emotion_tag)
            if tagged_mems:
                return tagged_mems[0]  # return the most intense memory of that tag
        if emotion_valence is not None:
            # Find memory with the smallest difference in valence
            best_memory = None
            best_diff = float('inf')
            for mem in self.memories:
                # Use mem.valence (default 0.0 if unknown tag) for comparison
                diff = abs(mem.valence - emotion_valence)
                if diff < best_diff - 1e-6:  # strictly smaller difference
                    best_diff = diff
                    best_memory = mem
                elif best_memory is not None and abs(diff - best_diff) < 1e-6:
                    # If valence difference is essentially a tie, prefer the more intense memory
                    if mem.intensity > best_memory.intensity:
                        best_memory = mem
                        # best_diff remains the same
            return best_memory
        # If no criteria provided or no memories, return None
        return None
class LivingMemoryKernel:
    """
    Manages the dynamic retrieval of memories from a MemoryCocoon based on current context.
    Acts as an interface between an agent's current state and its stored memories.
    """
    def __init__(self, memory_cocoon: MemoryCocoon):
        self.memory_cocoon = memory_cocoon
    def store_memory(self, content: str, emotion_tag: str, intensity: float = 1.0) -> MemoryItem:
        """
        Store a new memory in the cocoon.
        """
        return self.memory_cocoon.add_memory(content, emotion_tag, intensity)
    def retrieve_memory(self, emotion_tag: str = None, emotion_valence: float = None) -> MemoryItem:
        """
        Retrieve a memory that best matches the given emotional state.
        """
        return self.memory_cocoon.find_best_match(emotion_tag=emotion_tag, emotion_valence=emotion_valence)
    def retrieve_for_agent(self, agent) -> MemoryItem:
        """
        Convenience method to retrieve the best-matching memory for a given agent's current emotional state.
        Tries to match the agent's emotion tag first; if none found, falls back to valence matching.
        """
        # Attempt tag match first
        mem = None
        if agent.emotion_tag:
            mem = self.retrieve_memory(emotion_tag=agent.emotion_tag)
        if mem is None:
            # Fallback to valence if no exact tag match or no memory with that tag
            mem = self.retrieve_memory(emotion_valence=agent.emotion_valence)
        return mem
