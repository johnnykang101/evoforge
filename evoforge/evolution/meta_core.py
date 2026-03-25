"""Meta-Evolutionary Core (MEC).

Central engine that orchestrates architecture evolution.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

from evoforge.core.world_model import WorldModel as WorldModelAbstractor
from evoforge.core.causal_reader import CausalReader
from evoforge.core.synthesizer import KnowledgeSynthesizer
from evoforge.core.token_cache import TokenCache
from evoforge.core.context_compression import ContextCompressor
from evoforge.skills.cache import SkillCrystallizationCache
from evoforge.evolution.genome import ArchitectureGenome, GenomeParser
from evoforge.evolution.population import Population, PopulationConfig
from evoforge.evolution.variation import VariationConfig
from evoforge.evolution.fitness import FitnessEvaluator, FitnessWeights

logger = logging.getLogger(__name__)

@dataclass
class EvolutionConfig:
    """Configuration for meta-evolution."""
    population_size: int = 20
    generations: int = 50
    evaluations_per_genome: int = 5
    checkpoint_interval: int = 10
    weights: FitnessWeights = field(default_factory=FitnessWeights)

    # CKSE settings
    enable_ckse: bool = True
    ckse_update_frequency: int = 5  # Update knowledge every N generations

    # Variation settings
    mutation_rate: float = 0.1
    mutation_strength: float = 0.2
    crossover_rate: float = 0.5
    elitism_count: int = 2

class MetaEvolutionaryCore:
    """Orchestrates the autonomous evolution of agent architectures.

    The Meta-Evolutionary Core:
    1. Manages a population of architecture genomes
    2. Evaluates genome fitness through agent execution
    3. Applies genetic operators (mutation, crossover) to produce new generations
    4. Integrates CKSE insights to guide mutations (knowledge-directed evolution)
    5. Runs until convergence or generation limit
    6. Returns the best architecture configuration

    """

    def __init__(self, config: EvolutionConfig,
                 skill_cache: Optional[SkillCrystallizationCache] = None,
                 llm_client=None):
        """Initialize MEC.

        Args:
            config: Evolution configuration
            skill_cache: Skill cache for telemetry and execution
            llm_client: LLM client for CKSE components
        """
        self.config = config
        self.skill_cache = skill_cache
        self.llm_client = llm_client

        # Initialize CKSE components
        self.world_model = WorldModelAbstractor(llm_client)
        self.causal_reader = CausalReader(llm_client)
        self.knowledge_synthesizer = KnowledgeSynthesizer()
        from evoforge.core.genome_annotator import GenomeAnnotator  # lazy import — breaks circular dep
        self.genome_annotator = GenomeAnnotator()

        # Initialize population
        pop_config = PopulationConfig(
            size=config.population_size,
            variation=VariationConfig(
                mutation_rate=config.mutation_rate,
                mutation_strength=config.mutation_strength,
                crossover_rate=config.crossover_rate,
                elitism_count=config.elitism_count
            )
        )
        self.population = Population(pop_config)
        self.population.initialize()  # Start with default config + variations

        # Fitness evaluator
        self.fitness_evaluator = FitnessEvaluator(FitnessWeights())

        # Evolution state
        self.current_generation = 0
        self.best_genome: Optional[ArchitectureGenome] = None
        self.knowledge_units: List[Any] = []

    def evolve(self, task_suite: Optional[List[Any]] = None) -> ArchitectureGenome:
        """Run full evolution cycle.

        Args:
            task_suite: Optional list of tasks to evaluate on.
                       If None, uses default benchmark suite.

        Returns:
            Best genome after evolution
        """
        logger.info(f"Starting evolution: {self.config.population_size} genomes × {self.config.generations} generations")

        for generation in range(self.config.generations):
            self.current_generation = generation
            logger.info(f"Generation {generation + 1}/{self.config.generations}")

            # 1. Evaluate population fitness
            fitness_scores = self._evaluate_population(task_suite)
            self.population.fitness_scores = fitness_scores
            for i, score in enumerate(fitness_scores):
                self.population.genomes[i].fitness = score

            # 2. Track best genome
            best_idx = max(range(len(fitness_scores)), key=lambda i: fitness_scores[i])
            if not self.best_genome or fitness_scores[best_idx] > (self.best_genome.fitness or 0):
                self.best_genome = self.population.genomes[best_idx]
                logger.info(f"  New best: fitness={fitness_scores[best_idx]:.4f}")

            # 3. CKSE: Update knowledge (if enabled and due)
            if self.config.enable_ckse and generation % self.config.ckse_update_frequency == 0:
                self._update_knowledge()

            # 4. Evolve to next generation
            if generation < self.config.generations - 1:  # Don't evolve after final gen
                new_genomes = self.population.evolve()
                self.population.commit_generation(new_genomes)

            # 5. Logging
            stats = self.population.statistics()
            logger.info(f"  Stats: avg={stats['average_fitness']:.4f}, best={stats['best_fitness']:.4f}, div={stats['diversity']:.4f}")

            # 6. Checkpoint (optional)
            if generation % self.config.checkpoint_interval == 0:
                self._save_checkpoint(generation)

        logger.info(f"Evolution complete. Best fitness: {self.best_genome.fitness:.4f}")
        return self.best_genome

    def _evaluate_population(self, task_suite: Optional[List[Any]]) -> List[float]:
        """Evaluate all genomes in current population."""
        scores = []

        for i, genome in enumerate(self.population.genomes):
            # In real implementation, would run actual agent tasks
            # For now, use fitness evaluator with /simulation
            metrics = self.fitness_evaluator.evaluate_genome(genome)
            score = self.fitness_evaluator.scorer.compute(metrics)
            scores.append(score)
            self.population.update_fitness(i, score)

        return scores

    def _update_knowledge(self):
        """Update CKSE knowledge from recent execution telemetry."""
        # Placeholder: In production, would:
        # 1. Collect trajectories from recent agent executions
        # 2. Abstract with WorldModelAbstractor
        # 3. Extract insights with CausalReader
        # 4. Synthesize into KnowledgeUnits
        # 5. Use GenomeAnnotator to guide future mutations

        logger.info("  CKSE: Updating knowledge (placeholder)")
        self.knowledge_units = []  # Placeholder

    def _save_checkpoint(self, generation: int):
        """Save evolution checkpoint."""
        # Placeholder: In production, serialize best genome, population state,
        # knowledge units, and telemetry to disk
        pass

    def get_best_architecture(self) -> Dict[str, Any]:
        """Get the best architecture configuration discovered."""
        if not self.best_genome:
            return {}
        return self.best_genome.config

    def get_knowledge_units(self) -> List[Any]:
        """Retrieve current CKSE knowledge units."""
        return self.knowledge_units
