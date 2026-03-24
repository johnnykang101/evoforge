"""Population Management.

Manages a population of architecture genomes through evolution cycles.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from evoforge.evolution.genome import ArchitectureGenome
from evoforge.evolution.variation import VariationEngine, VariationConfig

@dataclass
class PopulationConfig:
    """Configuration for population."""
    size: int = 20
    variation: VariationConfig = field(default_factory=VariationConfig)

class Population:
    """Manages a population of architecture genomes.

    Responsibilities:
    - Initialize population with diversity
    - Track genomes and their fitness scores
    - Coordinate evolution via VariationEngine
    - Provide access to best/worst performers
    """

    def __init__(self, config: PopulationConfig):
        """Initialize population.

        Args:
            config: Population configuration
        """
        self.config = config
        self.genomes: List[ArchitectureGenome] = []
        self.fitness_scores: List[float] = []
        self.generation = 0
        self.variation_engine = VariationEngine(config.variation)

    def initialize(self, seed_config: Optional[Dict[str, Any]] = None):
        """Create initial population.

        Args:
            seed_config: Optional configuration to base initial population on.
                        If None, uses default config.
        """
        import random
        self.genomes = []

        for i in range(self.config.size):
            if i == 0 and seed_config:
                # First genome is seed config
                genome = ArchitectureGenome(config=seed_config)
            else:
                # Others are random variations
                if seed_config:
                    base = ArchitectureGenome(config=seed_config)
                    genome = base.mutate(mutation_rate=0.3, strength=0.5)
                else:
                    genome = ArchitectureGenome()  # Default config

            genome.generation = 0
            genome.parent_ids = []
            self.genomes.append(genome)

        self.fitness_scores = [0.0] * len(self.genomes)
        self.generation = 0

    def update_fitness(self, genome_id: int, fitness: float):
        """Update fitness score for a genome.

        Args:
            genome_id: Index in population
            fitness: Fitness score (higher is better, typically 0.0-1.0)
        """
        if 0 <= genome_id < len(self.genomes):
            self.fitness_scores[genome_id] = fitness
            self.genomes[genome_id].fitness = fitness

    def evolve(self) -> List[ArchitectureGenome]:
        """Produce next generation of genomes.

        Returns:
            New generation (does not replace current until committed)
        """
        new_genomes = self.variation_engine.create_next_generation(
            self.genomes, self.fitness_scores
        )
        return new_genomes

    def commit_generation(self, new_genomes: List[ArchitectureGenome]):
        """Replace current generation with new one."""
        self.genomes = new_genomes
        self.fitness_scores = [g.fitness or 0.0 for g in new_genomes]
        self.generation += 1

    def get_best_genomes(self, n: int = 1) -> List[ArchitectureGenome]:
        """Get top n genomes by fitness."""
        paired = list(zip(self.genomes, self.fitness_scores))
        paired.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in paired[:n]]

    def get_worst_genomes(self, n: int = 1) -> List[ArchitectureGenome]:
        """Get worst n genomes by fitness."""
        paired = list(zip(self.genomes, self.fitness_scores))
        paired.sort(key=lambda x: x[1])
        return [p[0] for p in paired[:n]]

    def get_average_fitness(self) -> float:
        """Calculate mean fitness of population."""
        if not self.fitness_scores:
            return 0.0
        return sum(self.fitness_scores) / len(self.fitness_scores)

    def get_diversity(self) -> float:
        """Estimate population diversity (0.0-1.0).

        Calculated as average pairwise Hamming distance between genomes.
        """
        if len(self.genomes) < 2:
            return 0.0

        total_distance = 0
        n_pairs = 0

        for i in range(len(self.genomes)):
            for j in range(i + 1, len(self.genomes)):
                dist = self._genome_distance(self.genomes[i], self.genomes[j])
                total_distance += dist
                n_pairs += 1

        return total_distance / n_pairs if n_pairs > 0 else 0.0

    def _genome_distance(self, g1: ArchitectureGenome, g2: ArchitectureGenome) -> float:
        """Compute distance between two genomes (0.0-1.0)."""
        # Simple approach: compare config values
        c1, c2 = g1.config, g2.config
        distance = 0.0
        count = 0

        def compare_dict(d1, d2, path=""):
            nonlocal distance, count
            for key in d1:
                if key in d2:
                    full_path = f"{path}.{key}" if path else key
                    if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                        compare_dict(d1[key], d2[key], full_path)
                    elif d1[key] != d2[key]:
                        distance += 1.0
                    count += 1

        compare_dict(c1, c2)
        return distance / count if count > 0 else 0.0

    def statistics(self) -> Dict[str, Any]:
        """Get population statistics."""
        return {
            "generation": self.generation,
            "size": len(self.genomes),
            "average_fitness": self.get_average_fitness(),
            "best_fitness": max(self.fitness_scores) if self.fitness_scores else 0.0,
            "worst_fitness": min(self.fitness_scores) if self.fitness_scores else 0.0,
            "diversity": self.get_diversity()
        }
