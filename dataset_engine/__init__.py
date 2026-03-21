"""
Codette Dataset Generation Engine
==================================

Production-quality dataset generation for LoRA adapter training.
Generates chat-format JSONL files for fine-tuning Llama 3.1 8B
on multi-perspective reasoning tasks.

Adapters supported:
    - newton: Classical physics and mechanics reasoning
    - davinci: Creative invention and cross-domain design
    - empathy: Emotional intelligence and compassionate reasoning
    - philosophy: Philosophical analysis and ethical reasoning
    - quantum: Quantum physics concepts and mathematics
    - consciousness: RC+xi recursive cognition framework
    - multi_perspective: Cross-perspective synthesis and integration
    - systems_architecture: AI system design and infrastructure
"""

from dataset_engine.template_registry import TemplateRegistry
from dataset_engine.answer_generator import AnswerGenerator
from dataset_engine.dataset_generator import DatasetGenerator

__all__ = [
    "TemplateRegistry",
    "AnswerGenerator",
    "DatasetGenerator",
]

__version__ = "1.0.0"
