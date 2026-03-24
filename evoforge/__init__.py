"""EvoForge: Self-Evolving AI Agent Framework.

A meta-morphic AI agent framework that continuously evolves its own
architecture through operational experience.
"""

__version__ = "0.1.0"
__author__ = "EvoForge AI"
__email__ = "contact@evoforge.ai"

# Core components
from .core.genome import (
    AgentGenome,
    ModuleGenome,
    ConnectionGenome,
    ModuleType,
    ConnectionType,
)
from .core.base import (
    BaseModule,
    PlannerModule,
    MemoryModule,
    SelectorModule,
    ExecutorModule,
    EvaluatorModule,
    ReflectorModule,
    ToolModule,
    ExecutionResult,
    create_module_from_genome,
)
from .core.world_model import WorldModel, WorldState
from .core.mec import MetaEvolutionaryCore, EvolutionConfig, FitnessMetrics, run_evolution
from .core.ckse import (
    ConvergentKnowledgeSynthesisEngine,
    KnowledgeUnit,
    KnowledgeType,
    CausalReader,
    KnowledgeSynthesizer,
    KnowledgeGenomeAnnotator,
)
from .core.skills import (
    SkillCrystallizationCache,
    Skill,
    SkillState,
    SkillMetrics,
    SkillExecution,
    ValidationResult,
    ChaîneValidator,
    TestSuite,
)

# Core components
from .core.genome import (
    AgentGenome,
    ModuleGenome,
    ConnectionGenome,
    ModuleType,
    ConnectionType,
)
from .core.base import (
    BaseModule,
    PlannerModule,
    MemoryModule,
    SelectorModule,
    ExecutorModule,
    EvaluatorModule,
    ReflectorModule,
    ToolModule,
    ExecutionResult,
    create_module_from_genome,
)
from .core.world_model import WorldModel, WorldState
from .core.mec import MetaEvolutionaryCore, EvolutionConfig, FitnessMetrics, run_evolution
from .core.ckse import (
    ConvergentKnowledgeSynthesisEngine,
    KnowledgeUnit,
    KnowledgeType,
    CausalReader,
    KnowledgeSynthesizer,
    KnowledgeGenomeAnnotator,
)
from .core.skills import (
    SkillCrystallizationCache,
    Skill,
    SkillState,
    SkillMetrics,
    SkillExecution,
    ValidationResult,
    ChaîneValidator,
    TestSuite,
)
