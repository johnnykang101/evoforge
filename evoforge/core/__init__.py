"""Convergent Knowledge Synthesis Engine (CKSE).

Cross-architecture learning system that extracts causal insights from agent
trajectories and uses them to guide architectural evolution.
"""

from .world_model import WorldModelAbstractor
from .causal_reader import CausalReader
from .synthesizer import KnowledgeSynthesizer
from .genome_annotator import GenomeAnnotator

__all__ = [
    "WorldModelAbstractor",
    "CausalReader",
    "KnowledgeSynthesizer",
    "GenomeAnnotator",
]
