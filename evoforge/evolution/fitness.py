"""Multi-Objective Fitness Evaluation.

Defines fitness functions and aggregator for evaluating architecture genomes.
Uses weighted combination of multiple objectives.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
if TYPE_CHECKING:
    from evoforge.evolution.genome import ArchitectureGenome
    from evoforge.core.fitness_ledger import FitnessLedger
    from evoforge.core.validation_battery import ValidationBattery
from evoforge.core.synthesizer import KnowledgeSynthesizer
from evoforge.skills.cache import SkillCrystallizationCache

@dataclass
class FitnessWeights:
    """Weights for multi-objective fitness."""
    task_success_rate: float = 0.35
    sample_efficiency: float = 0.25
    compute_efficiency: float = 0.20
    interpretability: float = 0.10
    stability: float = 0.10

    def normalize(self):
        """Normalize weights to sum to 1.0."""
        total = sum([
            self.task_success_rate,
            self.sample_efficiency,
            self.compute_efficiency,
            self.interpretability,
            self.stability
        ])
        if total > 0:
            self.task_success_rate /= total
            self.sample_efficiency /= total
            self.compute_efficiency /= total
            self.interpretability /= total
            self.stability /= total

@dataclass
class FitnessMetrics:
    """Container for fitness component metrics."""
    task_success_rate: float = 0.0
    sample_efficiency: float = 0.0  # Tokens per task (lower is better, will invert)
    compute_efficiency: float = 0.0  # Compute cost (will invert)
    interpretability: float = 0.0   # Architecture simplicity score
    stability: float = 0.0          # Lack of catastrophic forgetting

    def normalize(self):
        """Normalize metrics to 0.0-1.0 scale."""
        # Simple min-max normalization (would need reference ranges in production)
        # For now, saturate at 0-1
        pass

class MultiObjectiveFitness:
    """Computes aggregate fitness from multiple objectives.

    Fitness = w1 * success_rate
            + w2 * (1 - normalized_tokens)
            + w3 * (1 - normalized_compute)
            + w4 * interpretability_score
            + w5 * stability_score

    All components should be scaled to 0.0-1.0 before weighting.
    """

    def __init__(self, weights: Optional[FitnessWeights] = None):
        """Initialize fitness evaluator.

        Args:
            weights: Weights for each objective. If None, uses defaults.
        """
        self.weights = weights or FitnessWeights()
        self.weights.normalize()

    def compute(self, metrics: FitnessMetrics) -> float:
        """Compute aggregate fitness score.

        Args:
            metrics: Component metrics (should be pre-normalized to 0-1)

        Returns:
            Weighted fitness score (0.0-1.0)
        """
        # Ensure metrics are normalized
        metrics.normalize()

        fitness = (
            self.weights.task_success_rate * metrics.task_success_rate +
            self.weights.sample_efficiency * (1.0 - metrics.sample_efficiency) +
            self.weights.compute_efficiency * (1.0 - metrics.compute_efficiency) +
            self.weights.interpretability * metrics.interpretability +
            self.weights.stability * metrics.stability
        )

        return max(0.0, min(1.0, fitness))  # Clamp to 0-1

class FitnessEvaluator:
    """Evaluates genome fitness using actual agent execution.

    The Fitness Evaluator runs A/B tests between genome configurations:
    1. Instantiate agent with genome config
    2. Run benchmark tasks
    3. Collect metrics (success rate, tokens, compute, etc.)
    4. Compute fitness score using MultiObjectiveFitness
    """

    def __init__(
        self,
        fitness_config=None,
        battery: Optional['ValidationBattery'] = None,
    ):
        """Initialize evaluator.

        Args:
            fitness_config: Configuration for evaluation (task set, budget, etc.)
            battery: Optional ValidationBattery for real task evaluation.
                     When None, falls back to _simulate_* heuristics (backward compat).
        """
        self.config = fitness_config or {}
        self.scorer = MultiObjectiveFitness()
        self.battery = battery

    def evaluate_genome(
        self,
        genome: 'ArchitectureGenome',
        knowledge_synthesizer: Optional[KnowledgeSynthesizer] = None,
        ledger: Optional['FitnessLedger'] = None,
        battery: Optional['ValidationBattery'] = None,
    ) -> FitnessMetrics:
        """Evaluate a single genome by running agent with its configuration.

        Args:
            genome: The genome to evaluate
            knowledge_synthesizer: Optional CKSE synthesizer for knowledge-guided evaluation
            ledger: Optional FitnessLedger for cache-before-eval deduplication.
                    When None, behavior is identical to before (no breaking change).
            battery: Optional ValidationBattery override. Falls back to self.battery,
                     then to _simulate_* heuristics when neither is set.

        Returns:
            FitnessMetrics object with component scores
        """
        effective_battery = battery or self.battery

        # Cache-before-eval: hit → return reconstructed metrics; miss → continue
        if ledger is not None:
            from evoforge.core.fitness_ledger import compute_genome_hash
            ghash = compute_genome_hash(genome)
            cached = ledger.lookup(ghash)
            if cached is not None:
                return FitnessMetrics(
                    task_success_rate=cached.best_score,
                    sample_efficiency=cached.pareto_metrics.get("token_efficiency", 0.3),
                    compute_efficiency=cached.pareto_metrics.get("compute_efficiency", 0.4),
                    interpretability=cached.pareto_metrics.get("reasoning_quality", 0.5),
                    stability=0.9,
                )

        if effective_battery is not None:
            # Real task evaluation via ValidationBattery
            result = effective_battery.run(genome)
            pareto = result.to_pareto_metrics()
            metrics = FitnessMetrics(
                task_success_rate=pareto["task_completion_rate"],
                sample_efficiency=1.0 - pareto["token_efficiency"],
                compute_efficiency=self._simulate_compute_efficiency(genome),
                interpretability=pareto["reasoning_quality"],
                stability=0.9,
            )
        else:
            # Fallback: simulation heuristics (backward compat / cold-start safety)
            metrics = FitnessMetrics(
                task_success_rate=self._simulate_success_rate(genome),
                sample_efficiency=self._simulate_sample_efficiency(genome),
                compute_efficiency=self._simulate_compute_efficiency(genome),
                interpretability=self._assess_interpretability(genome),
                stability=0.9,
            )

        # Record to ledger on cache miss
        if ledger is not None:
            ledger.record(
                ghash,
                best_score=metrics.task_success_rate,
                pareto_metrics={
                    "task_completion_rate": metrics.task_success_rate,
                    "reasoning_quality": metrics.interpretability,
                    "token_efficiency": 1.0 - metrics.sample_efficiency,
                    "compute_efficiency": metrics.compute_efficiency,
                },
            )

        return metrics

    def _simulate_success_rate(self, genome: ArchitectureGenome) -> float:
        """Simulate success rate based on config (placeholder)."""
        # In production, actual execution
        config = genome.config

        # Simple heuristic: better planning = higher success
        base = 0.5

        if config.get('planning', {}).get('algorithm') == 'tree_of_thoughts':
            base += 0.15
        elif config.get('planning', {}).get('algorithm') == 'chain_of_thought':
            base += 0.10

        # Memory strategy matters
        mem_strategy = config.get('memory', {}).get('strategy')
        if mem_strategy == 'vector_db':
            base += 0.10
        elif mem_strategy == 'graph':
            base += 0.05

        return min(1.0, base + random.uniform(-0.05, 0.05))

    def _simulate_sample_efficiency(self, genome: ArchitectureGenome) -> float:
        """Simulate token efficiency (tokens per task, normalized 0-1)."""
        # Lower tokens = better efficiency = lower score here
        # So we return tokens used normalized to some range
        # In production, actual token counting
        base = 0.3  # Assume 30% of some baseline

        if genome.config.get('memory', {}).get('compression_strategy') == 'summarize':
            base -= 0.1

        return max(0.0, min(1.0, base))

    def _simulate_compute_efficiency(self, genome: ArchitectureGenome) -> float:
        """Simulate compute cost normalized to 0-1."""
        base = 0.4

        if genome.config.get('learning', {}).get('stable'):
            base += 0.1  # Stable optimization may cost more compute

        return max(0.0, min(1.0, base))

    def _assess_interpretability(self, genome: ArchitectureGenome) -> float:
        """Assess how interpretable the architecture is.

        Simpler architectures = more interpretable.
        """
        # Heuristic: fewer nested config levels = simpler
        config = genome.config

        def count_depth(d, depth=1):
            total = 0
            for v in d.values():
                if isinstance(v, dict):
                    total += count_depth(v, depth + 1)
                else:
                    total += depth
            return total

        complexity = count_depth(config)
        # Map complexity to 0-1 (lower complexity → higher interpretability)
        # Assume 5-20 depth range
        return max(0.0, min(1.0, 1.0 - (complexity - 5) / 15.0))

    def is_battery_improving(
        self,
        genome: 'ArchitectureGenome',
        ledger: 'FitnessLedger',
        window: int = 3,
    ) -> bool:
        """Return True if battery_score has improved over *window* consecutive runs.

        Walks the parent lineage from *genome* and checks that each successive
        entry's ``task_completion_rate`` is strictly greater than its ancestor.
        A genome with fewer than *window* ancestors returns False.

        Args:
            genome: The genome to assess.
            ledger: FitnessLedger containing lineage history.
            window: Minimum number of consecutive improvement steps required.

        Returns:
            True when the last *window* lineage entries show monotonic improvement.
        """
        from evoforge.core.fitness_ledger import compute_genome_hash
        ghash = compute_genome_hash(genome)
        chain = ledger.get_lineage(ghash)  # oldest-first list
        if len(chain) < window + 1:
            return False
        recent = chain[-(window + 1):]
        scores = [
            e.pareto_metrics.get("task_completion_rate", e.best_score)
            for e in recent
        ]
        return all(scores[i] < scores[i + 1] for i in range(len(scores) - 1))

    def evaluate_population(self, population: List[ArchitectureGenome]) -> List[float]:
        """Evaluate all genomes in population and return fitness scores."""
        scores = []
        for genome in population:
            metrics = self.evaluate_genome(genome)
            score = self.scorer.compute(metrics)
            scores.append(score)
        return scores

import random  # For simulation
