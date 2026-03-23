"""EvoForge: Self-Evolving AI Agent Framework.

A meta-morphic AI agent framework that continuously evolves its own
architecture through operational experience.
"""

__version__ = "0.2.0-dev"
__author__ = "EvoForge AI"
__email__ = "contact@evoforge.ai"

# Core components
from evoforge.core.ckse import WorldModelAbstractor, CausalReader, KnowledgeSynthesizer, GenomeAnnotator
from evoforge.skills.cache import SkillCrystallizationCache
from evoforge.skills.states import SkillState, SkillRecord
from evoforge.skills.validation import ValidationPipeline, ValidationStage
from evoforge.evolution.meta_core import MetaEvolutionaryCore
from evoforge.evolution.genome import ArchitectureGenome, GenomeParser
from evoforge.evolution.variation import VariationEngine
from evoforge.evolution.population import Population

__all__ = [
    # CKSE Components
    "WorldModelAbstractor",
    "CausalReader",
    "KnowledgeSynthesizer",
    "GenomeAnnotator",
    # Skill Cache
    "SkillCrystallizationCache",
    "SkillState",
    "SkillRecord",
    "ValidationPipeline",
    "ValidationStage",
    # Meta-Evolutionary Core
    "MetaEvolutionaryCore",
    "ArchitectureGenome",
    "GenomeParser",
    "VariationEngine",
    "Population",
]
