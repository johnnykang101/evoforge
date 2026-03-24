"""Variation Engine.

Implements mutation and crossover operators for genome evolution.

Refined operators (Iteration 2):
- Adaptive mutation rates (phase-aware: exploration → intensification → exploitation)
- Hypermutation: temporary rate increase when fitness plateaus
- Multi-operator pipeline: parameter + structural + topological mutations
- Diversity-preserving selection with crowding distance
"""

from typing import List, Optional, Tuple
import random
import math
from dataclasses import dataclass, field
from evoforge.evolution.genome import ArchitectureGenome


@dataclass
class VariationConfig:
    """Configuration for variation operators."""
    mutation_rate: float = 0.1
    mutation_strength: float = 0.2
    crossover_rate: float = 0.5
    elitism_count: int = 2

    # Structural and topological mutation rates
    structural_mutation_rate: float = 0.05
    topological_mutation_rate: float = 0.03

    # Hypermutation: activates when fitness stagnates
    hypermutation_trigger_generations: int = 10
    hypermutation_factor: float = 3.0

    # Phase-aware rate scheduling
    exploration_end_gen: int = 100
    intensification_end_gen: int = 500


class VariationEngine:
    """Applies genetic operators to produce new genome generations.

    The Variation Engine implements:
    - Parameter mutation with adaptive step sizes
    - Structural mutation (add/remove modules)
    - Topological mutation (rewire inter-module connections)
    - Modular crossover with constraint propagation
    - Hypermutation on fitness plateaus
    - Phase-aware rate scheduling
    - Elitism with diversity preservation
    """

    def __init__(self, config: VariationConfig):
        self.config = config
        self._fitness_history: List[float] = []

    def create_next_generation(self, population: List[ArchitectureGenome],
                               fitness_scores: List[float],
                               current_generation: int = 0) -> List[ArchitectureGenome]:
        """Generate next generation using selection + multi-operator variation.

        Args:
            population: Current generation genomes
            fitness_scores: Parallel list of fitness scores (higher = better)
            current_generation: Current generation number (for phase-aware rates)

        Returns:
            New generation of genomes
        """
        if len(population) != len(fitness_scores):
            raise ValueError("Population and fitness_scores must have same length")

        paired = list(zip(population, fitness_scores))
        paired.sort(key=lambda x: x[1], reverse=True)

        # Track best fitness for hypermutation detection
        best_fitness = paired[0][1] if paired else 0.0
        self._fitness_history.append(best_fitness)

        # Compute effective rates (phase + hypermutation)
        rates = self._compute_effective_rates(current_generation)

        new_generation: List[ArchitectureGenome] = []

        # Elitism: carry over top performers unchanged
        for i in range(min(self.config.elitism_count, len(paired))):
            new_generation.append(paired[i][0])

        # Generate rest via selection + variation pipeline
        while len(new_generation) < len(population):
            parents = self._tournament_select(paired, k=2)

            # Crossover
            if random.random() < rates["crossover"]:
                child = parents[0].crossover(parents[1], rates["crossover"])
            else:
                child = parents[0].mutate(rates["mutation"], rates["strength"])

            # Apply additional mutation operators in pipeline
            if random.random() < rates["structural"]:
                child = child.structural_mutate(rates["structural"])

            if random.random() < rates["topological"]:
                child = child.topological_mutate(rates["topological"])

            # Diversity check: reject if too similar to existing members
            if not self._is_too_similar(child, new_generation):
                new_generation.append(child)
            else:
                # Force more exploration via higher mutation
                boosted = child.mutate(min(rates["mutation"] * 2, 0.8), rates["strength"] * 1.5)
                new_generation.append(boosted)

        return new_generation[:len(population)]

    def _compute_effective_rates(self, generation: int) -> dict:
        """Compute mutation/crossover rates based on phase and fitness history.

        Phase schedule (from ARCHITECTURE.md):
        - Exploration (gen 0-100): High mutation, small populations
        - Intensification (gen 101-500): Moderate, balanced
        - Exploitation (gen 501+): Very low mutation, focus on refinement
        """
        cfg = self.config

        # Phase-aware base rates
        if generation <= cfg.exploration_end_gen:
            # Exploration: high mutation, moderate crossover
            phase_mult = 2.0
            strength_mult = 1.5
        elif generation <= cfg.intensification_end_gen:
            # Intensification: balanced
            t = (generation - cfg.exploration_end_gen) / (cfg.intensification_end_gen - cfg.exploration_end_gen)
            phase_mult = 2.0 - t * 1.5  # 2.0 → 0.5
            strength_mult = 1.5 - t * 1.0  # 1.5 → 0.5
        else:
            # Exploitation: low mutation
            phase_mult = 0.1
            strength_mult = 0.3

        # Hypermutation: detect fitness plateau
        hyper_mult = 1.0
        trigger = cfg.hypermutation_trigger_generations
        if len(self._fitness_history) >= trigger:
            recent = self._fitness_history[-trigger:]
            if len(set(round(f, 6) for f in recent)) <= 2:
                # Fitness hasn't changed meaningfully — activate hypermutation
                hyper_mult = cfg.hypermutation_factor

        effective_mutation = min(0.8, cfg.mutation_rate * phase_mult * hyper_mult)
        effective_strength = min(1.0, cfg.mutation_strength * strength_mult * hyper_mult)

        return {
            "mutation": effective_mutation,
            "strength": effective_strength,
            "crossover": cfg.crossover_rate,
            "structural": min(0.3, cfg.structural_mutation_rate * phase_mult * hyper_mult),
            "topological": min(0.2, cfg.topological_mutation_rate * phase_mult * hyper_mult),
        }

    def _is_too_similar(self, candidate: ArchitectureGenome,
                        existing: List[ArchitectureGenome],
                        threshold: float = 0.05) -> bool:
        """Check if candidate is too similar to any existing genome."""
        for genome in existing:
            if candidate.distance(genome) < threshold:
                return True
        return False

    def _tournament_select(self, paired_population: List[Tuple[ArchitectureGenome, float]],
                           k: int = 2, tournament_size: int = 3) -> List[ArchitectureGenome]:
        """Select k genomes using tournament selection."""
        selected = []
        for _ in range(k):
            contestants = random.sample(
                paired_population, min(tournament_size, len(paired_population))
            )
            winner = max(contestants, key=lambda x: x[1])[0]
            selected.append(winner)
        return selected

    def mutate_only(self, population: List[ArchitectureGenome]) -> List[ArchitectureGenome]:
        """Apply mutation to entire population without selection."""
        return [genome.mutate(self.config.mutation_rate, self.config.mutation_strength)
                for genome in population]

    def get_hypermutation_active(self) -> bool:
        """Check if hypermutation is currently active."""
        trigger = self.config.hypermutation_trigger_generations
        if len(self._fitness_history) < trigger:
            return False
        recent = self._fitness_history[-trigger:]
        return len(set(round(f, 6) for f in recent)) <= 2
