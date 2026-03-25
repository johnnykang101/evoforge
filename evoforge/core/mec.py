"""
EvoForge Core - Meta-Evolutionary Core (MEC).
Handles population management, selection, mutation, crossover, and evolution loop.
"""

from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import random
import time
import math
import uuid
from collections import deque

from .genome import AgentGenome, ModuleGenome, ModuleType, ConnectionGenome, ConnectionType
from .base import create_module_from_genome, BaseModule, ExecutionResult


class SelectionStrategy(Enum):
    """Selection strategies for parent choice."""
    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK = "rank"
    ELITISM = "elitism"


@dataclass
class EvolutionConfig:
    """Configuration for the evolutionary process."""
    population_size: int = 50
    num_generations: int = 1000
    elite_count: int = 5
    tournament_size: int = 8
    mutation_rate: float = 0.1
    mutation_intensity: float = 0.2
    crossover_rate: float = 0.7
    diversity_lambda: float = 0.3  # Weight for novelty in selection
    max_retries: int = 3  # Number of retries to produce valid offspring


@dataclass
class FitnessMetrics:
    """Detailed fitness breakdown."""
    success_rate: float = 0.0
    efficiency: float = 0.0
    interpretability: float = 0.0
    novelty: float = 0.0
    composite_score: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "success_rate": self.success_rate,
            "efficiency": self.efficiency,
            "interpretability": self.interpretability,
            "novelty": self.novelty,
            "composite_score": self.composite_score
        }


class MetaEvolutionaryCore:
    """
    The Meta-Evolutionary Core (MEC) manages the evolutionary process.
    It maintains a population of agent genomes and applies selection,
    crossover, and mutation operators to evolve them across generations.
    """

    def __init__(self, config: EvolutionConfig, fitness_evaluator: 'FitnessEvaluator'):
        self.config = config
        self.fitness_evaluator = fitness_evaluator
        self.population: List[AgentGenome] = []
        self.generation: int = 0
        self.history: List[Dict[str, Any]] = []
        self.best_genomes: List[AgentGenome] = []
        self.feature_space_cache: Dict[str, List[float]] = {}  # For novelty computation
        self.novelty_window_size: int = 100  # Number of past genomes for novelty baseline

    def initialize_population(self, seed_architectures: List[AgentGenome] = None) -> None:
        """
        Initialize the population. If seed_architectures provided, use them
        and fill remaining slots with random variations.
        """
        if seed_architectures:
            self.population = [g.copy() for g in seed_architectures[:self.config.population_size]]
            # Add mutations to fill out population
            while len(self.population) < self.config.population_size:
                parent = random.choice(seed_architectures)
                child = parent.mutate(self.config.mutation_rate, self.config.mutation_intensity)
                self.population.append(child)
        else:
            # Generate random initial population using module factory
            self.population = [self._create_random_agent(i) for i in range(self.config.population_size)]

        self._update_feature_space_cache()

    def _create_random_agent(self, idx: int) -> AgentGenome:
        """Create a random valid agent architecture."""
        import uuid
        genome = AgentGenome(
            id=str(uuid.uuid4()),
            name=f"RandomAgent_{idx}",
            modules=[],
            connections=[],
            generation=self.generation
        )

        # Create 2-5 random modules
        num_modules = random.randint(2, 5)
        module_types = list(ModuleType)

        module_ids = []
        for i in range(num_modules):
            mod_type = random.choice(module_types)
            mod_genome = ModuleGenome(
                id=str(uuid.uuid4()),
                type=mod_type,
                name=f"{mod_type.value}_{i}",
                config={"strategy": random.choice(["sequential", "parallel", "greedy", "recent"])},
                parameters={
                    "max_steps": random.randint(1, 10),
                    "timeout": random.uniform(1, 30),
                    "temperature": random.uniform(0.1, 2.0)
                }
            )
            genome.add_module(mod_genome)
            module_ids.append(mod_genome.id)

        # Create random connections ensuring a single connected component
        if len(module_ids) >= 2:
            random.shuffle(module_ids)
            for i in range(len(module_ids) - 1):
                conn = ConnectionGenome(
                    id=str(uuid.uuid4()),
                    source_module_id=module_ids[i],
                    target_module_id=module_ids[i+1],
                    connection_type=random.choice(list(ConnectionType))
                )
                genome.add_connection(conn)

            # Add some extra random connections
            num_extra = random.randint(0, 2)
            for _ in range(num_extra):
                source, target = random.sample(module_ids, 2)
                if source != target:
                    conn = ConnectionGenome(
                        id=str(uuid.uuid4()),
                        source_module_id=source,
                        target_module_id=target,
                        connection_type=random.choice(list(ConnectionType))
                    )
                    genome.add_connection(conn)

        return genome

    def evolve_generation(self) -> Dict[str, Any]:
        """Perform one generation of evolution."""
        start_time = time.time()

        # 1. Evaluate fitness for all genomes (if not already evaluated)
        unevaluated = [g for g in self.population if g.fitness == 0.0]
        for genome in unevaluated:
            fitness = self.fitness_evaluator.evaluate(genome)
            genome.fitness = fitness.composite_score
            # Store metrics in genome's metadata
            genome.metrics = fitness.to_dict() if not hasattr(genome, 'metrics') else genome.metrics

        # 2. Select parents and generate offspring
        new_population = self._selection_and_reproduction()

        # 3. Apply mutations to offspring
        for genome in new_population[self.config.elite_count:]:
            if random.random() < self.config.mutation_rate:
                genome.mutate_connections(self.config.mutation_rate)
            if random.random() < self.config.mutation_rate * 0.5:
                genome = genome.mutate(self.config.mutation_rate, self.config.mutation_intensity)

        self.population = new_population
        self.generation += 1

        # 4. Update statistics
        stats = self._compute_generation_stats()
        self.history.append(stats)

        # 5. Update feature space cache for novelty computation
        self._update_feature_space_cache()

        stats["duration_seconds"] = time.time() - start_time
        return stats

    def _selection_and_reproduction(self) -> List[AgentGenome]:
        """
        Select parents and produce next generation population.
        Uses multi-tournament selection with diversity bonus.
        """
        # Sort population by fitness (descending)
        sorted_pop = sorted(self.population, key=lambda g: g.fitness, reverse=True)

        # Keep elites unchanged
        elites = [g.copy() for g in sorted_pop[:self.config.elite_count]]
        new_population = elites.copy()

        # Fill remainder with offspring
        while len(new_population) < self.config.population_size:
            # Tournament selection with diversity bonus
            parent1 = self._tournament_select_with_diversity(sorted_pop)
            parent2 = self._tournament_select_with_diversity(sorted_pop)

            if random.random() < self.config.crossover_rate:
                child = parent1.crossover(parent2)
            else:
                child = parent1.copy() if parent1.fitness >= parent2.fitness else parent2.copy()

            # Ensure child is valid (retry if needed)
            child_accepted = False
            for attempt in range(self.config.max_retries):
                if child.is_valid:
                    new_population.append(child)
                    child_accepted = True
                    break
                else:
                    # Mutate to try to fix validity
                    child = child.mutate(self.config.mutation_rate, self.config.mutation_intensity)

            if not child_accepted:
                # Fallback to a random valid parent
                valid_parents = [p for p in [parent1, parent2] if p.is_valid]
                if valid_parents:
                    new_population.append(random.choice(valid_parents).copy())
                else:
                    # Extreme fallback: create random agent
                    new_population.append(self._create_random_agent(len(new_population)))

        return new_population[:self.config.population_size]

    def _tournament_select_with_diversity(self, sorted_pop: List[AgentGenome]) -> AgentGenome:
        """
        Tournament selection with diversity bonus.
        Selects k random candidates, then picks the one maximizing:
        fitness + λ * novelty
        """
        candidates = random.sample(
            sorted_pop,
            min(self.config.tournament_size, len(sorted_pop))
        )

        best_candidate = None
        best_score = -float('inf')

        for candidate in candidates:
            fitness_score = candidate.fitness
            novelty_score = self._compute_novelty(candidate)

            combined = fitness_score + self.config.diversity_lambda * novelty_score

            if combined > best_score:
                best_score = combined
                best_candidate = candidate

        return best_candidate

    def _compute_novelty(self, genome: AgentGenome) -> float:
        """
        Compute novelty as average distance to k-nearest neighbors in feature space.
        Feature space is defined by architectural characteristics.
        """
        # Get or compute feature vector for this genome
        features = self._extract_feature_vector(genome)

        if len(self.feature_space_cache) < 10:  # Not enough cache yet
            return 0.0

        # Compute distances to cached genomes
        distances = []
        for cached_id, cached_features in self.feature_space_cache.items():
            dist = self._euclidean_distance(features, cached_features)
            distances.append(dist)

        # Novelty is average distance to k-nearest neighbors (k=5)
        k = min(5, len(distances))
        if k == 0:
            return 0.0
        nearest = sorted(distances)[:k]
        return sum(nearest) / k

    def _extract_feature_vector(self, genome: AgentGenome) -> List[float]:
        """
        Extract a feature vector representing the architecture.
        Normalized to [0, 1] range for distance computation.
        """
        num_modules = len(genome.modules)
        num_connections = len(genome.connections)

        # Module type distribution
        type_counts = {t: 0 for t in ModuleType}
        for m in genome.modules:
            type_counts[m.type] += 1
        type_ratios = [type_counts[t] / max(num_modules, 1) for t in ModuleType]

        # Average parameters per module
        avg_params = sum(len(m.parameters) for m in genome.modules) / max(num_modules, 1)

        # Connection density
        max_connections = num_modules * (num_modules - 1) if num_modules > 1 else 1
        density = num_connections / max_connections

        # Depth (longest path from any entry point)
        depth = self._compute_graph_depth(genome) / max(num_modules, 1)

        features = type_ratios + [avg_params, density, depth]
        return features

    def _compute_graph_depth(self, genome: AgentGenome) -> int:
        """Compute the longest path length in the module dependency graph."""
        if not genome.connections:
            return 1

        # Build adjacency list
        adj = {m.id: [] for m in genome.modules}
        for conn in genome.connections:
            adj[conn.source_module_id].append(conn.target_module_id)

        # Find entry nodes (no incoming edges)
        incoming = set(c.target_module_id for c in genome.connections)
        entry_nodes = [m.id for m in genome.modules if m.id not in incoming]

        max_depth = 0
        memo = {}
        visiting = set()

        def dfs(node: str) -> int:
            if node in memo:
                return memo[node]
            if node in visiting:
                return 0  # cycle detected — break recursion
            if not adj[node]:
                memo[node] = 1
                return 1
            visiting.add(node)
            depth = 1 + max(dfs(neighbor) for neighbor in adj[node])
            visiting.discard(node)
            memo[node] = depth
            return depth

        for node in entry_nodes:
            max_depth = max(max_depth, dfs(node))

        return max_depth

    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Compute Euclidean distance between two vectors."""
        if len(v1) != len(v2):
            return float('inf')
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _update_feature_space_cache(self) -> None:
        """Update cache of feature vectors for novelty computation."""
        # Keep last N genomes in cache
        all_genomes = [g for g in self.population if g.fitness > 0]  # Only evaluated
        if len(all_genomes) > self.novelty_window_size:
            all_genomes = all_genomes[-self.novelty_window_size:]

        self.feature_space_cache = {}
        for genome in all_genomes:
            features = self._extract_feature_vector(genome)
            self.feature_space_cache[genome.id] = features

    def _compute_generation_stats(self) -> Dict[str, Any]:
        """Compute statistics for the current generation."""
        fitnesses = [g.fitness for g in self.population]
        avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        best_idx = max(range(len(self.population)), key=lambda i: self.population[i].fitness)
        best_genome = self.population[best_idx]

        # Track best ever
        if not self.best_genomes or best_genome.fitness > self.best_genomes[-1].fitness:
            self.best_genomes.append(best_genome.copy())

        stats = {
            "generation": self.generation,
            "population_size": len(self.population),
            "avg_fitness": avg_fitness,
            "max_fitness": max(fitnesses) if fitnesses else 0.0,
            "min_fitness": min(fitnesses) if fitnesses else 0.0,
            "best_genome_id": best_genome.id,
            "best_genome_name": best_genome.name,
            "best_fitness": best_genome.fitness,
            "avg_modules": sum(len(g.modules) for g in self.population) / len(self.population),
            "avg_connections": sum(len(g.connections) for g in self.population) / len(self.population)
        }
        return stats

    def get_best_genome(self, n: int = 1) -> List[AgentGenome]:
        """Get top-n genomes by fitness."""
        sorted_pop = sorted(self.population, key=lambda g: g.fitness, reverse=True)
        return sorted_pop[:n]

    def save_checkpoint(self, path: str) -> None:
        """Save current population state."""
        import json
        checkpoint = {
            "generation": self.generation,
            "config": self.config.__dict__,
            "population": [g.to_dict() for g in self.population],
            "best_genomes": [g.to_dict() for g in self.best_genomes],
            "history": self.history[-100:]  # Last 100 generations
        }
        with open(path, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    def load_checkpoint(self, path: str) -> None:
        """Load population from checkpoint."""
        import json
        with open(path, 'r') as f:
            checkpoint = json.load(f)

        self.generation = checkpoint["generation"]
        self.population = [AgentGenome.from_dict(g) for g in checkpoint["population"]]
        self.best_genomes = [AgentGenome.from_dict(g) for g in checkpoint["best_genomes"]]
        self.history = checkpoint["history"]
        self._update_feature_space_cache()


def run_evolution(
    mec: MetaEvolutionaryCore,
    num_generations: Optional[int] = None,
    early_stopping_patience: int = 20,
    plateau_threshold: float = 0.001
) -> Tuple[List[AgentGenome], Dict[str, Any]]:
    """
    Run the full evolutionary loop.

    Args:
        mec: Initialized MetaEvolutionaryCore
        num_generations: Override config if specified
        early_stopping_patience: Stop if no improvement for N generations
        plateau_threshold: Minimum improvement to count as improvement

    Returns:
        Tuple of (best_genomes, run_stats)
    """
    if num_generations is None:
        num_generations = mec.config.num_generations

    start_time = time.time()
    best_fitness_history = []
    patience_counter = 0

    for gen in range(num_generations):
        stats = mec.evolve_generation()
        current_best = stats["best_fitness"]
        best_fitness_history.append(current_best)

        # Check for early stopping
        if gen >= early_stopping_patience:
            recent_best = max(best_fitness_history[-early_stopping_patience:])
            if current_best - recent_best < plateau_threshold:
                patience_counter += 1
            else:
                patience_counter = 0

            if patience_counter >= early_stopping_patience:
                print(f"Early stopping at generation {gen}: plateau detected")
                break

        if gen % 10 == 0:
            print(f"Gen {gen}: Best={current_best:.4f}, Avg={stats['avg_fitness']:.4f}")

    run_time = time.time() - start_time
    final_best = mec.get_best_genome(1)[0]

    run_stats = {
        "generations_completed": mec.generation,
        "total_time_seconds": run_time,
        "final_best_fitness": final_best.fitness,
        "best_genome": final_best.to_dict(),
        "fitness_history": best_fitness_history
    }

    return mec.get_best_genome(5), run_stats
