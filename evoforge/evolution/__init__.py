"""Meta-Evolutionary Core (MEC).

Architecture mutation, crossover, and fitness-based selection engine.
"""

from .genome import ArchitectureGenome
from .variation import VariationEngine
from .population import Population
from .meta_core import MetaEvolutionaryCore

__all__ = [
    "ArchitectureGenome",
    "VariationEngine",
    "Population",
    "MetaEvolutionaryCore",
]
