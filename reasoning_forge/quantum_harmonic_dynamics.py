
import math, random
from reasoning_forge.multi_perspective_agents import Agent
class QuantumHarmonicDynamics:
    """
    Simulates the multi-agent synchronization with quantum-inspired behavior.
    Manages entanglement links between agents and updates their states over time applying:
      - Memory influence and intent modulation for each agent.
      - Coupling (entanglement) between agents to induce synchronization (resonance).
      - Quantum tunneling effects for sudden state changes.
      - Decoherence to occasionally remove entanglements.
    """
    def __init__(self):
        self.agents = []            # List of Agent objects in the simulation
        self.entangled_pairs = []   # List of tuples (agentA, agentB) representing entangled agent pairs
        # Parameters to control the dynamics:
        self.coupling_strength = 0.1      # How strongly entangled agents pull each other (0 = no coupling, 1 = immediate sync)
        self.tunneling_prob_factor = 5.0  # Factor for tunneling probability decay; higher = lower tunneling chance for same diff
        self.decoherence_rate = 0.02      # Probability per update step that an entangled pair decoheres (link breaks)
    def add_agent(self, agent: Agent):
        """
        Add an Agent to the simulation.
        """
        self.agents.append(agent)
    def entangle(self, agent1: Agent, agent2: Agent):
        """
        Entangle two agents, establishing a coupling between their states.
        """
        if agent1 is agent2:
            return  # cannot entangle an agent with itself
        # Avoid duplicate entanglement entries
        for (a, b) in self.entangled_pairs:
            if (a is agent1 and b is agent2) or (a is agent2 and b is agent1):
                return  # already entangled
        self.entangled_pairs.append((agent1, agent2))
        agent1.entangled_with.append(agent2)
        agent2.entangled_with.append(agent1)
    def disentangle(self, agent1: Agent, agent2: Agent):
        """
        Remove entanglement between two agents, if it exists.
        """
        # Remove from entangled_pairs list
        self.entangled_pairs = [pair for pair in self.entangled_pairs
                                 if not ((pair[0] is agent1 and pair[1] is agent2) or
                                         (pair[0] is agent2 and pair[1] is agent1))]
        # Remove references in each agent's entangled_with list
        if agent2 in agent1.entangled_with:
            agent1.entangled_with.remove(agent2)
        if agent1 in agent2.entangled_with:
            agent2.entangled_with.remove(agent1)
    def update(self):
        """
        Advance the simulation by one time step:
          1. Each agent retrieves a resonant memory and modulates its own intent/emotion.
          2. All entangled pairs are then harmonized (coupled) toward each other (synchronization).
          3. Apply quantum tunneling: some agents may make sudden jumps in intent if large differences remain.
          4. Apply decoherence: randomly break some entanglements (and slightly reset those agents toward baseline).
        """
        # 1. Memory influence on each agent
        for agent in self.agents:
            mem = agent.recall_memory()
            if mem:
                # Modulate intent based on memory's emotional valence and intensity.
                # A positive memory increases intent, a negative memory decreases it.
                delta = mem.valence * 0.1 * mem.intensity
                agent.modulate_intent(delta)
                # Adjust agent's current emotion toward the memory's emotion.
                agent.adjust_emotion(mem.valence)
        # 2. Coupling for entangled agents (synchronization/resonance)
        for (a, b) in list(self.entangled_pairs):  # use list(...) to avoid issues if we modify entangled_pairs during loop
            # Calculate differences in state
            intent_diff = a.intent - b.intent
            emo_diff = a.emotion_valence - b.emotion_valence
            # Pull both intents toward each other (diffusive coupling)
            a.intent -= intent_diff * self.coupling_strength
            b.intent += intent_diff * self.coupling_strength
            # Pull both emotional valences toward each other
            a.emotion_valence -= emo_diff * self.coupling_strength
            b.emotion_valence += emo_diff * self.coupling_strength
            # After coupling, update qualitative emotion tags based on new valences
            if a.emotion_valence > 0.1:
                a.emotion_tag = "positive" if a.emotion_valence >= 0.5 else "slightly positive"
            elif a.emotion_valence < -0.1:
                a.emotion_tag = "negative" if a.emotion_valence <= -0.5 else "slightly negative"
            else:
                a.emotion_tag = "neutral"
            if b.emotion_valence > 0.1:
                b.emotion_tag = "positive" if b.emotion_valence >= 0.5 else "slightly positive"
            elif b.emotion_valence < -0.1:
                b.emotion_tag = "negative" if b.emotion_valence <= -0.5 else "slightly negative"
            else:
                b.emotion_tag = "neutral"
            # 3. Quantum tunneling effect: allow sudden jump if large disparity remains
            # Recalculate difference magnitude after coupling adjustment
            intent_diff = abs(a.intent - b.intent)
            if intent_diff > 1e-6:  # any non-zero difference
                # Probability decays exponentially with difference
                # (Small differences => prob ~1, large differences => prob ~0)
                prob = math.exp(-self.tunneling_prob_factor * intent_diff)
                if random.random() < prob:
                    # We trigger a tunneling event: the agent with lower intent jumps closer to the higher's intent
                    if a.intent > b.intent:
                        # b is behind a; bring b up by closing half the gap
                        b.intent += intent_diff * 0.5
                    else:
                        # a is behind b
                        a.intent += intent_diff * 0.5
        # 4. Decoherence: randomly break entanglements
        for (a, b) in list(self.entangled_pairs):
            if random.random() < self.decoherence_rate:
                # Break the entanglement link
                self.disentangle(a, b)
                # After decoherence, gently steer each agent back toward its baseline intent and neutral emotion
                if hasattr(a, 'base_intent'):
                    a.intent = (a.intent + a.base_intent) / 2.0
                if hasattr(b, 'base_intent'):
                    b.intent = (b.intent + b.base_intent) / 2.0
                # Dampen emotions (assuming environment measurement causes loss of emotional intensity)
                a.emotion_valence *= 0.5
                b.emotion_valence *= 0.5
                # Update emotion tags post-decoherence
                if a.emotion_valence > 0.1:
                    a.emotion_tag = "positive" if a.emotion_valence >= 0.5 else "slightly positive"
                elif a.emotion_valence < -0.1:
                    a.emotion_tag = "negative" if a.emotion_valence <= -0.5 else "slightly negative"
                else:
                    a.emotion_tag = "neutral"
                if b.emotion_valence > 0.1:
                    b.emotion_tag = "positive" if b.emotion_valence >= 0.5 else "slightly positive"
                elif b.emotion_valence < -0.1:
                    b.emotion_tag = "negative" if b.emotion_valence <= -0.5 else "slightly negative"
                else:
                    b.emotion_tag = "neutral"
