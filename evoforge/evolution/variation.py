"""Variation Engine.

Implements mutation and crossover operators for genome evolution.
"""

from typing import List, Tuple
import random
from dataclasses import dataclass
from evoforge.evolution.genome import ArchitectureGenome

@dataclass
class VariationConfig:
    """Configuration for variation operators."""
    mutation_rate: float = 0.1
    mutation_strength: float = 0.2
    crossover_rate: float = 0.5
    elitism_count: int = 2  # Number of best genomes to preserve unchanged

class VariationEngine:
    """Applies genetic operators to produce new genome generations.

    The Variation Engine implements:
    - Mutation: Random perturbations to existing parameters
    - Crossover: Combining two parent genomes into child
    - Elitism: Preserving top performers unchanged

    The goal is to explore the architecture configuration space
    while maintaining successful traits from parents.
    """

    def __init__(self, config: VariationConfig):
        """Initialize variation engine with configuration.

        Args:
            config: Variation parameters (rates, strength, elitism)
        """
        self.config = config

    def create_next_generation(self, population: List[ArchitectureGenome],
                               fitness_scores: List[float]) -> List[ArchitectureGenome]:
        """Generate next generation using tournament selection + variation.

        Args:
            population: Current generation genomes
            fitness_scores: Parallel list of fitness scores (higher = better)

        Returns:
            New generation of genomes
        """
        if len(population) != len(fitness_scores):
            raise ValueError("Population and fitness_scores must have same length")

        # Pair genomes with their fitness
        paired = list(zip(population, fitness_scores))
        # Sort by fitness descending
        paired.sort(key=lambda x: x[1], reverse=True)

        new_generation = []

        # Elitism: carry over top performers unchanged
        for i in range(min(self.config.elitism_count, len(paired))):
            new_generation.append(paired[i][0])

        # Generate rest of generation via selection + variation
        while len(new_generation) < len(population):
            # Tournament selection (size 3)
            parents = self._tournament_select(paired, k=2)

            # Crossover
            if random.random() < self.config.crossover_rate:
                child = parents[0].crossover(parents[1], self.config.crossover_rate)
            else:
                # No crossover, just clone first parent
                child = parents[0].mutate(self.config.mutation_rate, self.config.mutation_strength)

            new_generation.append(child)

        return new_generation[:len(population)]  # Trim excess

    def _tournament_select(self, paired_population: List[Tuple[ArchitectureGenome, float]], k: int = 3) -> List[ArchitectureGenome]:
        """Select k genomes using tournament selection."""
        selected = []
        for _ in range(k):
            # Randomly pick 3 contestants
            contestants = random.sample(paired_population, min(3, len(paired_population)))
            # Winner is highest fitness
            winner = max(contestants, key=lambda x: x[1])[0]
            selected.append(winner)
        return selected

    def mutate_only(self, population: List[ArchitectureGenome]) -> List[ArchitectureGenome]:
        """Apply mutation to entire population without selection."""
        return [genome.mutate(self.config.mutation_rate, self.config.mutation_strength)
                for genome in population]
