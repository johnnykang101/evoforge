"""Model Router — Cost-aware model selection based on task complexity.

Routes tasks to cheaper models when possible, reserving expensive models
for complex reasoning. Tracks cost savings vs baseline (always-expensive).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class ModelTier:
    name: str
    cost_per_1k_tokens: float  # USD per 1K tokens
    max_context: int
    quality_ceiling: float  # 0-100 reasoning quality ceiling


# OpenRouter free-tier models mapped to cost tiers
DEFAULT_MODEL_TIERS: Dict[TaskComplexity, ModelTier] = {
    TaskComplexity.SIMPLE: ModelTier(
        name="meta-llama/llama-3-8b-instruct:free",
        cost_per_1k_tokens=0.0,
        max_context=8192,
        quality_ceiling=60.0,
    ),
    TaskComplexity.MODERATE: ModelTier(
        name="mistralai/mistral-7b-instruct:free",
        cost_per_1k_tokens=0.0,
        max_context=32768,
        quality_ceiling=75.0,
    ),
    TaskComplexity.COMPLEX: ModelTier(
        name="google/gemma-2-9b-it:free",
        cost_per_1k_tokens=0.0,
        max_context=8192,
        quality_ceiling=85.0,
    ),
}

# Reference cost tiers for savings calculation (as if using paid models)
REFERENCE_COSTS: Dict[TaskComplexity, float] = {
    TaskComplexity.SIMPLE: 0.10,   # $/1K tokens for a cheap paid model
    TaskComplexity.MODERATE: 0.50,  # $/1K tokens for a mid-tier model
    TaskComplexity.COMPLEX: 2.00,  # $/1K tokens for a top-tier model
}

BASELINE_COST_PER_1K = 2.00  # If we always used the expensive model


@dataclass
class RoutingDecision:
    task_id: str
    complexity: TaskComplexity
    selected_model: ModelTier
    tokens_used: int
    actual_cost: float
    baseline_cost: float  # Cost if we had used the expensive model

    @property
    def savings(self) -> float:
        return self.baseline_cost - self.actual_cost


@dataclass
class CostTracker:
    """Accumulates cost metrics across a benchmark run."""
    decisions: List[RoutingDecision] = field(default_factory=list)

    def record(self, decision: RoutingDecision):
        self.decisions.append(decision)

    @property
    def total_actual_cost(self) -> float:
        return sum(d.actual_cost for d in self.decisions)

    @property
    def total_baseline_cost(self) -> float:
        return sum(d.baseline_cost for d in self.decisions)

    @property
    def total_savings(self) -> float:
        return self.total_baseline_cost - self.total_actual_cost

    @property
    def savings_pct(self) -> float:
        if self.total_baseline_cost == 0:
            return 0.0
        return (self.total_savings / self.total_baseline_cost) * 100.0

    @property
    def routing_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {"simple": 0, "moderate": 0, "complex": 0}
        for d in self.decisions:
            dist[d.complexity.value] += 1
        return dist

    def summary(self) -> Dict:
        return {
            "total_tasks": len(self.decisions),
            "total_actual_cost_usd": round(self.total_actual_cost, 4),
            "total_baseline_cost_usd": round(self.total_baseline_cost, 4),
            "total_savings_usd": round(self.total_savings, 4),
            "savings_pct": round(self.savings_pct, 1),
            "routing_distribution": self.routing_distribution,
        }


class ModelRouter:
    """Routes tasks to appropriate model tiers based on complexity."""

    def __init__(self, model_tiers: Optional[Dict[TaskComplexity, ModelTier]] = None):
        self.tiers = model_tiers or DEFAULT_MODEL_TIERS
        self.tracker = CostTracker()

    def classify_complexity(self, task_description: str, token_count: int) -> TaskComplexity:
        """Classify task complexity using heuristics.

        Rules:
        - Short tasks (<500 tokens) with no reasoning keywords -> SIMPLE
        - Medium tasks or single-step reasoning -> MODERATE
        - Long tasks, multi-step reasoning, or code generation -> COMPLEX
        """
        desc_lower = task_description.lower()
        complex_keywords = [
            "analyze", "debug", "architect", "design", "optimize",
            "refactor", "multi-step", "chain-of-thought", "prove",
        ]
        moderate_keywords = [
            "explain", "summarize", "compare", "convert", "translate",
            "review", "evaluate",
        ]

        has_complex = any(kw in desc_lower for kw in complex_keywords)
        has_moderate = any(kw in desc_lower for kw in moderate_keywords)

        if has_complex or token_count > 2000:
            return TaskComplexity.COMPLEX
        elif has_moderate or token_count > 500:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE

    def route(self, task_id: str, task_description: str, token_count: int) -> RoutingDecision:
        """Route a task to the appropriate model and record the decision."""
        complexity = self.classify_complexity(task_description, token_count)
        model = self.tiers[complexity]
        ref_cost = REFERENCE_COSTS[complexity]

        actual_cost = (token_count / 1000.0) * ref_cost
        baseline_cost = (token_count / 1000.0) * BASELINE_COST_PER_1K

        decision = RoutingDecision(
            task_id=task_id,
            complexity=complexity,
            selected_model=model,
            tokens_used=token_count,
            actual_cost=actual_cost,
            baseline_cost=baseline_cost,
        )
        self.tracker.record(decision)
        return decision

    def get_cost_summary(self) -> Dict:
        return self.tracker.summary()
