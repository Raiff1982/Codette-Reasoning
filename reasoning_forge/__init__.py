"""
Reasoning Forge - Multi-Agent Reasoning Training Data Generator

The reasoning forge takes concepts and generates high-quality multi-perspective
reasoning training data. Each agent analyzes from its unique perspective, a critic
evaluates the ensemble, and a synthesis engine combines them into coherent training examples.

New in v2.0:
  - EpistemicMetrics: RC+xi tension/coherence measurement
  - QuantumSpiderweb: 5D belief propagation + attractor detection
  - CocoonSync: Federated encrypted state synchronization
  - ForgeEngine.forge_with_feedback(): Closed critic loop
  - ForgeEngine.forge_with_debate(): Multi-turn agent debate
"""

from reasoning_forge.event_embedded_value import (
    ContinuousInterval,
    DiscreteEvent,
    EEVAnalysis,
    EventEmbeddedValueEngine,
    RiskFrontierComparison,
)

try:
    from reasoning_forge.forge_engine import ForgeEngine
    from reasoning_forge.agents.base_agent import ReasoningAgent
    from reasoning_forge.agents.newton_agent import NewtonAgent
    from reasoning_forge.agents.quantum_agent import QuantumAgent
    from reasoning_forge.agents.ethics_agent import EthicsAgent
    from reasoning_forge.agents.philosophy_agent import PhilosophyAgent
    from reasoning_forge.agents.davinci_agent import DaVinciAgent
    from reasoning_forge.agents.empathy_agent import EmpathyAgent
    from reasoning_forge.agents.critic_agent import CriticAgent
    from reasoning_forge.synthesis_engine import SynthesisEngine
    from reasoning_forge.problem_generator import ProblemGenerator
    from reasoning_forge.epistemic_metrics import EpistemicMetrics
    from reasoning_forge.quantum_spiderweb import QuantumSpiderweb, NodeState, IdentityGlyph
    from reasoning_forge.cocoon_sync import CocoonSync, CocoonKeyManager
except Exception:
    ForgeEngine = None
    ReasoningAgent = None
    NewtonAgent = None
    QuantumAgent = None
    EthicsAgent = None
    PhilosophyAgent = None
    DaVinciAgent = None
    EmpathyAgent = None
    CriticAgent = None
    SynthesisEngine = None
    ProblemGenerator = None
    EpistemicMetrics = None
    QuantumSpiderweb = None
    NodeState = None
    IdentityGlyph = None
    CocoonSync = None
    CocoonKeyManager = None

# v2.1: observability + rich cocoon schema
try:
    from reasoning_forge.reasoning_trace import ReasoningTrace, TraceEvent
    from reasoning_forge.cocoon_schema_v2 import Cocoon, build_cocoon
    from reasoning_forge.living_memory import LivingMemoryKernel
    from reasoning_forge.living_memory_v2 import LivingMemoryKernelV2, MemoryCocoonV2
except Exception:
    ReasoningTrace = None
    TraceEvent = None
    Cocoon = None
    build_cocoon = None
    LivingMemoryKernel = None
    LivingMemoryKernelV2 = None
    MemoryCocoonV2 = None

__all__ = [
    # v2.0 core
    "ForgeEngine",
    "ReasoningAgent",
    "NewtonAgent",
    "QuantumAgent",
    "EthicsAgent",
    "PhilosophyAgent",
    "DaVinciAgent",
    "EmpathyAgent",
    "CriticAgent",
    "SynthesisEngine",
    "ProblemGenerator",
    "EpistemicMetrics",
    "QuantumSpiderweb",
    "NodeState",
    "IdentityGlyph",
    "CocoonSync",
    "CocoonKeyManager",
    "ContinuousInterval",
    "DiscreteEvent",
    "EEVAnalysis",
    "EventEmbeddedValueEngine",
    "RiskFrontierComparison",
    # v2.1 observability + schema
    "ReasoningTrace",
    "TraceEvent",
    "Cocoon",
    "build_cocoon",
    "LivingMemoryKernel",
    "LivingMemoryKernelV2",
    "MemoryCocoonV2",
]

__version__ = "2.1.0"
