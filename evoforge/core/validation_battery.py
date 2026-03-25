"""ValidationBattery — 30-task deterministic evaluation suite.

Replaces _simulate_* heuristics in FitnessEvaluator with deterministic
task execution against known ground-truth answers.

Each task has a ``scoring_fn`` key that maps to a built-in checker. The
battery runs all 30 tasks and returns a BatteryResult whose
``to_pareto_metrics()`` feeds directly into ParetoSelection.

When no ``infer_fn`` is supplied to ``ValidationBattery.run()``, performance
is simulated from genome config (cold-start safety — mirrors the existing
``_simulate_*`` approach in FitnessEvaluator until a real LLM client is wired).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from evoforge.evolution.genome import ArchitectureGenome

from evoforge.core.model_router import ModelRouter


# ---------------------------------------------------------------------------
# Deterministic scoring functions
# ---------------------------------------------------------------------------

def _score_exact_match(response: str, expected: str) -> bool:
    return response.strip().lower() == expected.strip().lower()


def _score_numeric_match(response: str, expected: str, tol: float = 1e-6) -> bool:
    try:
        return abs(float(response.strip()) - float(expected.strip())) <= tol
    except ValueError:
        return False


def _score_contains(response: str, expected: str) -> bool:
    return expected.strip().lower() in response.strip().lower()


def _score_boolean_match(response: str, expected: str) -> bool:
    r = response.strip().lower()
    e = expected.strip().lower()
    true_vals = {"true", "yes", "correct"}
    false_vals = {"false", "no", "incorrect"}
    if e in true_vals:
        return r in true_vals
    if e in false_vals:
        return r in false_vals
    return r == e


_SCORING_FNS: Dict[str, Callable[[str, str], bool]] = {
    "exact_match": _score_exact_match,
    "numeric_match": _score_numeric_match,
    "contains": _score_contains,
    "boolean_match": _score_boolean_match,
}

# Default difficulty weights per category
_CATEGORY_DIFFICULTY: Dict[str, float] = {
    "math": 1.0,
    "code": 1.2,
    "logic": 1.1,
    "language": 0.9,
}

# Baseline tokens assumed per task for efficiency normalization
_BASELINE_TOKENS_PER_TASK = 500


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationTask:
    """A single deterministic evaluation task with a known correct answer."""

    task_id: str
    category: str          # "math" | "code" | "logic" | "language"
    prompt: str
    expected_answer: str
    scoring_fn: str        # key into _SCORING_FNS
    difficulty: float = 1.0

    def check(self, response: str) -> bool:
        """Return True if *response* matches the expected answer."""
        fn = _SCORING_FNS.get(self.scoring_fn, _score_exact_match)
        return fn(response, self.expected_answer)


@dataclass
class ValidationResult:
    """Outcome of running a single ValidationTask."""

    task_id: str
    passed: bool
    latency_ms: float
    tokens_used: int
    difficulty: float = 1.0


@dataclass
class BatteryResult:
    """Aggregate result across all tasks in a single battery run.

    ``to_pareto_metrics()`` returns the dict consumed by ParetoSelection
    (and recorded into FitnessLedger).
    """

    task_completion_rate: float    # passed / total
    reasoning_quality: float       # difficulty-weighted pass rate
    token_efficiency: float        # 0-1, higher = fewer tokens used
    raw_results: List[ValidationResult] = field(default_factory=list)

    def to_pareto_metrics(self) -> Dict[str, float]:
        """Return ParetoMetrics dict for ParetoSelection / FitnessLedger."""
        return {
            "task_completion_rate": self.task_completion_rate,
            "reasoning_quality": self.reasoning_quality,
            "token_efficiency": self.token_efficiency,
        }


# ---------------------------------------------------------------------------
# ValidationBattery
# ---------------------------------------------------------------------------

class ValidationBattery:
    """Runs a fixed suite of deterministic evaluation tasks.

    Loads tasks from a JSON file (``evoforge/data/battery_v1.json``).
    Execution is routed through ModelRouter for cost-aware model selection.

    Usage::

        battery = ValidationBattery.load("evoforge/data/battery_v1.json")
        result  = battery.run(genome)
        metrics = result.to_pareto_metrics()   # → ParetoSelection

    To use a real LLM, pass ``infer_fn=(task_id, prompt) → str`` to ``run()``.
    When *infer_fn* is None, genome-config-based simulation is used (backward
    compatible with the existing ``_simulate_*`` pattern).
    """

    def __init__(
        self,
        tasks: List[ValidationTask],
        router: Optional[ModelRouter] = None,
    ) -> None:
        self.tasks = tasks
        self.router = router or ModelRouter()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: str,
        router: Optional[ModelRouter] = None,
    ) -> "ValidationBattery":
        """Load battery tasks from a JSON file.

        Args:
            path: Path to battery JSON (absolute or relative to cwd).
            router: Optional ModelRouter; a default instance is created if None.

        Returns:
            Populated ValidationBattery ready to run.

        Raises:
            FileNotFoundError: If *path* does not exist.
            KeyError: If a required JSON field is missing.
        """
        p = Path(path)
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        tasks: List[ValidationTask] = []
        for entry in data:
            category = entry["category"]
            tasks.append(ValidationTask(
                task_id=entry["id"],
                category=category,
                prompt=entry["prompt"],
                expected_answer=entry["expected_answer"],
                scoring_fn=entry.get("scoring_fn", "exact_match"),
                difficulty=entry.get(
                    "difficulty",
                    _CATEGORY_DIFFICULTY.get(category, 1.0),
                ),
            ))
        return cls(tasks=tasks, router=router)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        genome: "ArchitectureGenome",
        infer_fn: Optional[Callable[[str, str], str]] = None,
    ) -> BatteryResult:
        """Evaluate *genome* against all tasks.

        Args:
            genome: The genome under evaluation (config drives simulation
                    when *infer_fn* is None).
            infer_fn: Optional ``(task_id, prompt) → response_str`` callable
                      for real LLM execution. When None, uses genome-config
                      simulation for cold-start safety.

        Returns:
            BatteryResult with Pareto-ready metrics.
        """
        raw: List[ValidationResult] = []
        total_tokens = 0

        for task in self.tasks:
            t0 = time.monotonic()

            # Route to model tier; use prompt word-count as token estimate
            routing = self.router.route(
                task.task_id,
                task.prompt,
                len(task.prompt.split()),
            )
            tokens_used = routing.tokens_used

            response = (
                infer_fn(task.task_id, task.prompt)
                if infer_fn is not None
                else self._simulate_response(task, genome)
            )

            passed = task.check(response)
            latency_ms = (time.monotonic() - t0) * 1_000.0
            total_tokens += tokens_used

            raw.append(ValidationResult(
                task_id=task.task_id,
                passed=passed,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                difficulty=task.difficulty,
            ))

        return self._aggregate(raw, total_tokens)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _simulate_response(
        self,
        task: ValidationTask,
        genome: "ArchitectureGenome",
    ) -> str:
        """Simulate a response using genome config heuristics.

        Mirrors the ``_simulate_success_rate`` approach in FitnessEvaluator.
        Returns the correct answer or a sentinel wrong answer based on a
        deterministic probability derived from the genome config, so repeated
        calls on the same (genome, task) pair always produce the same result.
        """
        import random

        config = genome.config if hasattr(genome, "config") else {}

        # Base pass probability per category
        base: Dict[str, float] = {
            "math": 0.55,
            "code": 0.45,
            "logic": 0.50,
            "language": 0.65,
        }
        prob = base.get(task.category, 0.50)

        # Planning algorithm bonus
        planning_algo = config.get("planning", {}).get("algorithm", "")
        if planning_algo == "tree_of_thoughts":
            prob += 0.15
        elif planning_algo == "chain_of_thought":
            prob += 0.10

        # Memory strategy bonus
        mem_strategy = config.get("memory", {}).get("strategy", "")
        if mem_strategy == "vector_db":
            prob += 0.08
        elif mem_strategy == "graph":
            prob += 0.04

        prob = min(prob, 0.95)

        # Seed from (config, task_id) for reproducibility
        seed = hash(str(sorted(config.items())) + task.task_id) & 0xFFFF_FFFF
        rng = random.Random(seed)
        return task.expected_answer if rng.random() < prob else "__wrong__"

    def _aggregate(
        self,
        raw: List[ValidationResult],
        total_tokens: int,
    ) -> BatteryResult:
        """Compute aggregate Pareto metrics from individual task results."""
        if not raw:
            return BatteryResult(
                task_completion_rate=0.0,
                reasoning_quality=0.0,
                token_efficiency=0.0,
                raw_results=raw,
            )

        n = len(raw)
        task_completion_rate = sum(1 for r in raw if r.passed) / n

        weight_sum = sum(r.difficulty for r in raw)
        weighted_pass = sum(r.difficulty for r in raw if r.passed)
        reasoning_quality = weighted_pass / weight_sum if weight_sum > 0 else 0.0

        avg_tokens = total_tokens / n
        token_efficiency = max(0.0, 1.0 - (avg_tokens / _BASELINE_TOKENS_PER_TASK))
        token_efficiency = min(1.0, token_efficiency)

        return BatteryResult(
            task_completion_rate=task_completion_rate,
            reasoning_quality=reasoning_quality,
            token_efficiency=token_efficiency,
            raw_results=raw,
        )
