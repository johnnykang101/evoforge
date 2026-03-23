"""
EvoForge Core - Base module interfaces and implementations.
Defines the contract for all evolvable modules.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from .genome import ModuleGenome, ModuleType


@dataclass
class ExecutionResult:
    """Standardized result from module execution."""
    success: bool
    output: Any
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "metadata": self.metadata or {},
            "error": self.error
        }


class BaseModule(ABC):
    """
    Abstract base class for all evolvable modules in EvoForge.
    Each module has a well-defined interface and can be composed
    into agent architectures via connections.
    """

    def __init__(self, genome: ModuleGenome):
        self.genome = genome
        self.type = genome.type
        self.name = genome.name
        self.config = genome.config
        self.parameters = genome.parameters

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        """
        Execute the module's primary function.
        Args:
            context: Shared state dictionary containing inputs from connected modules
        Returns:
            ExecutionResult with output and status
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Check if the module configuration and internal state are valid."""
        pass

    def update_parameters(self, new_parameters: Dict[str, Any]):
        """Update module parameters (called during evolution)."""
        self.parameters.update(new_parameters)
        self.genome.parameters.update(new_parameters)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genome": self.genome.to_dict(),
            "type": self.type.value,
            "name": self.name
        }

    @classmethod
    @abstractmethod
    def create(cls, config: Dict[str, Any]) -> 'BaseModule':
        """Factory method to create a module from configuration."""
        pass


class PlannerModule(BaseModule):
    """
    Planner modules take goals and context, produce execution plans.
    Supports multiple planning strategies.
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.strategy = self.config.get("strategy", "sequential")
        self.max_steps = self.parameters.get("max_steps", 10)
        self.plan_history: List[List[Dict[str, Any]]] = []

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        goal = context.get("goal", "")
        if not goal:
            return ExecutionResult(False, None, error="No goal provided")

        plan = self._generate_plan(goal, context)
        self.plan_history.append(plan)

        return ExecutionResult(True, {"plan": plan, "steps": len(plan)})

    def validate(self) -> bool:
        return self.strategy in ["sequential", "parallel", "hierarchical", "iterative"]

    def _generate_plan(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a plan based on strategy."""
        if self.strategy == "sequential":
            return self._plan_sequential(goal, context)
        elif self.strategy == "hierarchical":
            return self._plan_hierarchical(goal, context)
        elif self.strategy == "iterative":
            return self._plan_iterative(goal, context)
        else:
            return self._plan_parallel(goal, context)

    def _plan_sequential(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simple sequential step-by-step plan."""
        steps = []
        # In a real implementation, this could use an LLM or planning algorithm
        # For now, decompose based on keywords
        words = goal.split()
        num_steps = min(self.max_steps, len(words) // 2 + 1)
        for i in range(num_steps):
            steps.append({
                "step_id": i,
                "description": f"Execute step {i+1} toward: {goal}",
                "type": "action",
                "estimated_effort": 1.0
            })
        return steps

    def _plan_hierarchical(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create high-level goals that can be further decomposed."""
        return [
            {"step_id": 0, "description": f"Achieve: {goal}", "type": "goal", "subtasks": []},
        ]

    def _plan_parallel(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan multiple parallel tasks."""
        steps = []
        for i in range(min(3, self.max_steps)):
            steps.append({
                "step_id": i,
                "description": f"Parallel task {i+1} for: {goal}",
                "type": "parallel_action",
                "estimated_effort": 0.5
            })
        return steps

    def _plan_iterative(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan with a feedback loop."""
        return [
            {"step_id": 0, "description": f"Initial attempt at: {goal}", "type": "action"},
            {"step_id": 1, "description": "Evaluate outcome", "type": "evaluation"},
            {"step_id": 2, "description": "Refine based on feedback", "type": "refinement"},
            {"step_id": 3, "description": "Execute refined plan", "type": "action"},
        ]

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'PlannerModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.PLANNER,
            name=config.get("name", "DefaultPlanner"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


class MemoryModule(BaseModule):
    """
    Memory modules store and retrieve information across executions.
    Supports different memory types (episodic, semantic, procedural).
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.memory_type = self.config.get("memory_type", "episodic")
        self.storage: List[Dict[str, Any]] = []
        self.max_size = self.parameters.get("max_size", 1000)
        self.retrieval_strategy = self.config.get("retrieval_strategy", "recent")

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        operation = context.get("memory_operation", "retrieve")
        key = context.get("key")
        value = context.get("value")

        if operation == "store" and key is not None:
            return self._store(key, value, context)
        elif operation == "retrieve" and key is not None:
            return self._retrieve(key, context)
        elif operation == "search":
            query = context.get("query", "")
            return self._search(query, context)
        elif operation == "summarize":
            return self._summarize(context)
        else:
            return ExecutionResult(False, None, error=f"Invalid operation: {operation}")

    def _store(self, key: str, value: Any, context: Dict[str, Any]) -> ExecutionResult:
        entry = {
            "key": key,
            "value": value,
            "timestamp": __import__('time').time(),
            "metadata": context.get("metadata", {})
        }
        self.storage.append(entry)
        if len(self.storage) > self.max_size:
            self.storage.pop(0)  # FIFO eviction
        return ExecutionResult(True, {"stored": key})

    def _retrieve(self, key: str, context: Dict[str, Any]) -> ExecutionResult:
        if self.retrieval_strategy == "recent":
            for entry in reversed(self.storage):
                if entry["key"] == key:
                    return ExecutionResult(True, {"value": entry["value"]})
        else:
            for entry in self.storage:
                if entry["key"] == key:
                    return ExecutionResult(True, {"value": entry["value"]})
        return ExecutionResult(False, None, error=f"Key not found: {key}")

    def _search(self, query: str, context: Dict[str, Any]) -> ExecutionResult:
        """Simple keyword-based search across stored entries."""
        results = []
        query_lower = query.lower()
        for entry in self.storage:
            if (query_lower in str(entry["key"]).lower() or
                query_lower in str(entry["value"]).lower()):
                results.append(entry)
        return ExecutionResult(True, {"results": results, "count": len(results)})

    def _summarize(self, context: Dict[str, Any]) -> ExecutionResult:
        summary = {
            "total_entries": len(self.storage),
            "memory_type": self.memory_type,
            "oldest_timestamp": min(e["timestamp"] for e in self.storage) if self.storage else None,
            "recent_keys": [e["key"] for e in self.storage[-5:]]
        }
        return ExecutionResult(True, summary)

    def validate(self) -> bool:
        return self.memory_type in ["episodic", "semantic", "procedural"]
        1.0

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'MemoryModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.MEMORY,
            name=config.get("name", "DefaultMemory"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


class SelectorModule(BaseModule):
    """
    Selector modules choose between alternative actions or modules.
    Implements various selection strategies.
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.strategy = self.config.get("strategy", "greedy")
        self.temperature = self.parameters.get("temperature", 1.0)
        self.top_k = self.parameters.get("top_k", 3)

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        options = context.get("options", [])
        if not options:
            return ExecutionResult(False, None, error="No options to select from")

        scores = context.get("scores", [])
        if not scores:
            scores = [self._evaluate_option(opt, context) for opt in options]

        selected_idx = self._select(strategy=self.strategy, options=options, scores=scores)
        selected = options[selected_idx] if selected_idx is not None else None

        return ExecutionResult(True, {
            "selected": selected,
            "index": selected_idx,
            "score": scores[selected_idx] if selected_idx is not None else None
        })

    def _evaluate_option(self, option: Any, context: Dict[str, Any]) -> float:
        """Simple heuristic scoring (can be overridden)."""
        if isinstance(option, dict):
            return option.get("score", option.get("priority", 0.0))
        return float(option) if isinstance(option, (int, float)) else 0.5

    def _select(self, strategy: str, options: List[Any], scores: List[float]) -> Optional[int]:
        if not scores:
            return None

        if strategy == "greedy":
            idx = scores.index(max(scores))
            return idx

        elif strategy == "softmax":
            import math
            import random
            # Apply temperature and sample
            scaled_scores = [s / self.temperature for s in scores]
            max_score = max(scaled_scores)
            exp_scores = [math.exp(s - max_score) for s in scaled_scores]
            total = sum(exp_scores)
            probs = [e / total for e in exp_scores]
            return random.choices(range(len(options)), weights=probs)[0]

        elif strategy == "top_k":
            # Randomly select from top-k options
            top_k_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:self.top_k]
            return random.choice(top_k_indices)

        elif strategy == "epsilon_greedy":
            import random
            if random.random() < 0.1:  # epsilon=0.1
                return random.choice(range(len(options)))
            return scores.index(max(scores))

        else:
            return scores.index(max(scores))

    def validate(self) -> bool:
        return self.strategy in ["greedy", "softmax", "top_k", "epsilon_greedy"] and self.temperature > 0

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'SelectorModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.SELECTOR,
            name=config.get("name", "DefaultSelector"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


class ExecutorModule(BaseModule):
    """
    Executor modules perform actions, call tools, or invoke sub-modules.
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.execution_mode = self.config.get("mode", "direct")
        self.timeout = self.parameters.get("timeout", 30)
        self.max_retries = self.parameters.get("max_retries", 3)

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        task = context.get("task")
        if task is None:
            return ExecutionResult(False, None, error="No task provided")

        return self._execute_task(task, context)

    def _execute_task(self, task: Any, context: Dict[str, Any]) -> ExecutionResult:
        """Execute the given task with retry logic."""
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                if self.execution_mode == "direct":
                    result = self._execute_direct(task, context)
                elif self.execution_mode == "delegated":
                    result = self._execute_delegated(task, context)
                else:
                    result = ExecutionResult(False, None, error=f"Unknown mode: {self.execution_mode}")

                if result.success:
                    return result
                else:
                    last_error = result.error
            except Exception as e:
                last_error = str(e)

            attempts += 1

        return ExecutionResult(False, None, error=f"Task failed after {self.max_retries} attempts: {last_error}")

    def _execute_direct(self, task: Any, context: Dict[str, Any]) -> ExecutionResult:
        """Direct execution (synchronous)."""
        if callable(task):
            try:
                output = task()
                return ExecutionResult(True, output)
            except Exception as e:
                return ExecutionResult(False, None, error=str(e))
        else:
            return ExecutionResult(True, {"task": task, "status": "queued"})

    def _execute_delegated(self, task: Any, context: Dict[str, Any]) -> ExecutionResult:
        """Delegated execution (asynchronous or external)."""
        # In a full implementation, this could send to a worker queue or external agent
        return ExecutionResult(True, {"task": task, "status": "delegated"})

    def validate(self) -> bool:
        return self.execution_mode in ["direct", "delegated"] and self.timeout > 0 and self.max_retries >= 0

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'ExecutorModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.EXECUTOR,
            name=config.get("name", "DefaultExecutor"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


class EvaluatorModule(BaseModule):
    """
    Evaluator modules assess execution outcomes and produce feedback scores.
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.metrics = self.config.get("metrics", ["success", "efficiency"])
        self.weights = self.parameters.get("weights", {})
        self.threshold = self.parameters.get("threshold", 0.5)

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        outcome = context.get("outcome")
        expected = context.get("expected")

        if outcome is None:
            return ExecutionResult(False, None, error="No outcome to evaluate")

        scores = self._compute_metrics(outcome, expected, context)
        overall = self._aggregate_scores(scores)

        return ExecutionResult(True, {
            "scores": scores,
            "overall": overall,
            "pass": overall >= self.threshold
        })

    def _compute_metrics(self, outcome: Any, expected: Any, context: Dict[str, Any]) -> Dict[str, float]:
        scores = {}
        for metric in self.metrics:
            if metric == "success":
                scores["success"] = 1.0 if outcome == expected else 0.0
            elif metric == "accuracy":
                # Simple accuracy for numeric/string comparison
                scores["accuracy"] = 1.0 if str(outcome) == str(expected) else 0.0
            elif metric == "efficiency":
                time_taken = context.get("time_taken", 1.0)
                scores["efficiency"] = 1.0 / max(time_taken, 0.001)
            elif metric == "completeness":
                # Check if all required keys/fields are present
                if isinstance(outcome, dict):
                    required = set(context.get("required_keys", []))
                    present = set(outcome.keys())
                    scores["completeness"] = len(present & required) / max(len(required), 1)
                else:
                    scores["completeness"] = 1.0
            else:
                scores[metric] = 0.5  # Unknown metric
        return scores

    def _aggregate_scores(self, scores: Dict[str, float]) -> float:
        if not scores:
            return 0.0
        total_weight = 0.0
        weighted_sum = 0.0
        for metric, score in scores.items():
            weight = self.weights.get(metric, 1.0)
            weighted_sum += score * weight
            total_weight += weight
        return weighted_sum / max(total_weight, 1e-6)

    def validate(self) -> bool:
        return all(w >= 0 for w in self.weights.values()) and 0 <= self.threshold <= 1

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'EvaluatorModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.EVALUATOR,
            name=config.get("name", "DefaultEvaluator"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


class ReflectorModule(BaseModule):
    """
    Reflector modules analyze execution traces to extract insights and
    propose improvements (meta-evolution input).
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.analysis_depth = self.parameters.get("analysis_depth", 3)
        self.insight_categories = self.config.get("categories", ["performance", "failure_patterns", "optimizations"])

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        execution_trace = context.get("execution_trace", [])
        if not execution_trace:
            return ExecutionResult(False, None, error="No execution trace provided")

        insights = self._analyze_trace(execution_trace, context)
        suggestions = self._generate_suggestions(insights, context)

        return ExecutionResult(True, {
            "insights": insights,
            "suggestions": suggestions,
            "summary": self._summarize_insights(insights)
        })

    def _analyze_trace(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        insights = []
        for entry in trace[-self.analysis_depth:]:
            if entry.get("success") is False:
                insights.append({
                    "type": "failure",
                    "module": entry.get("module"),
                    "error": entry.get("error"),
                    "severity": "high"
                })
            elif entry.get("duration", 0) > context.get("timeout", 10):
                insights.append({
                    "type": "performance",
                    "module": entry.get("module"),
                    "issue": "slow_execution",
                    "duration": entry.get("duration")
                })
        return insights

    def _generate_suggestions(self, insights: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        suggestions = []
        for insight in insights:
            if insight["type"] == "failure":
                suggestions.append({
                    "target": insight["module"],
                    "action": "increase_retries" if "timeout" in insight["error"] else "adjust_parameters",
                    "confidence": 0.7
                })
            elif insight["type"] == "performance":
                suggestions.append({
                    "target": insight["module"],
                    "action": "optimize_algorithm",
                    "confidence": 0.6
                })
        return suggestions

    def _summarize_insights(self, insights: List[Dict[str, Any]]) -> str:
        if not insights:
            return "No significant issues detected."
        failure_count = sum(1 for i in insights if i["type"] == "failure")
        perf_count = sum(1 for i in insights if i["type"] == "performance")
        return f"Found {failure_count} failures and {perf_count} performance issues. Generated {len(self._generate_suggestions(insights, {}))} improvement suggestions."

    def validate(self) -> bool:
        return self.analysis_depth > 0 and len(self.insight_categories) > 0

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'ReflectorModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.REFLECTOR,
            name=config.get("name", "DefaultReflector"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


class ToolModule(BaseModule):
    """
    Tool modules wrap external APIs, functions, or capabilities.
    """

    def __init__(self, genome: ModuleGenome):
        super().__init__(genome)
        self.tool_name = self.config.get("tool_name", "generic")
        self.endpoint = self.config.get("endpoint", "")
        self.timeout = self.parameters.get("timeout", 10)

    def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        query = context.get("query", "")
        if not query:
            return ExecutionResult(False, None, error="No query provided for tool")

        return self._invoke_tool(query, context)

    def _invoke_tool(self, query: Any, context: Dict[str, Any]) -> ExecutionResult:
        # In a full implementation, this would call an external API or function
        if self.endpoint:
            # Simulated external call
            return ExecutionResult(True, {
                "tool": self.tool_name,
                "result": f"Mock result for: {query}",
                "source": "external"
            })
        else:
            return ExecutionResult(True, {
                "tool": self.tool_name,
                "result": query,
                "source": "internal"
            })

    def validate(self) -> bool:
        return bool(self.tool_name)

    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'ToolModule':
        genome = ModuleGenome(
            id=str(uuid.uuid4()),
            type=ModuleType.TOOL,
            name=config.get("name", "DefaultTool"),
            config=config,
            parameters=config.get("parameters", {})
        )
        return cls(genome)


# Module factory mapping
MODULE_FACTORIES = {
    ModuleType.PLANNER: PlannerModule.create,
    ModuleType.MEMORY: MemoryModule.create,
    ModuleType.SELECTOR: SelectorModule.create,
    ModuleType.EXECUTOR: ExecutorModule.create,
    ModuleType.EVALUATOR: EvaluatorModule.create,
    ModuleType.REFLECTOR: ReflectorModule.create,
    ModuleType.TOOL: ToolModule.create,
}


def create_module_from_genome(genome: ModuleGenome) -> BaseModule:
    """Instantiate a module from its genome using the appropriate factory."""
    factory = MODULE_FACTORIES.get(genome.type)
    if factory is None:
        raise ValueError(f"Unknown module type: {genome.type}")
    return factory(genome.config)
