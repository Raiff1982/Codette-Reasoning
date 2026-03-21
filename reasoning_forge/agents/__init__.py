"""
Reasoning Forge Agents

Each agent analyzes concepts from a distinct intellectual perspective,
producing substantive domain-specific reasoning.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent
from reasoning_forge.agents.newton_agent import NewtonAgent
from reasoning_forge.agents.quantum_agent import QuantumAgent
from reasoning_forge.agents.ethics_agent import EthicsAgent
from reasoning_forge.agents.philosophy_agent import PhilosophyAgent
from reasoning_forge.agents.davinci_agent import DaVinciAgent
from reasoning_forge.agents.empathy_agent import EmpathyAgent
from reasoning_forge.agents.critic_agent import CriticAgent

__all__ = [
    "ReasoningAgent",
    "NewtonAgent",
    "QuantumAgent",
    "EthicsAgent",
    "PhilosophyAgent",
    "DaVinciAgent",
    "EmpathyAgent",
    "CriticAgent",
]
