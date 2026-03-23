"""World Model Abstractor.

Converts raw agent execution trajectories into comparable state representations.
Abstracts away implementation-specific details to enable cross-architecture learning.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

class StateCategory(Enum):
    """Categories of world states for abstraction."""
    OBSERVATION = "observation"
    ACTION = "action"
    OUTCOME = "outcome"
    ERROR = "error"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"

@dataclass
class WorldState:
    """Abstracted state representation."""
    category: StateCategory
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    state_id: str = field(default_factory=lambda: WorldModelAbstractor._generate_state_id(""))

    @staticmethod
    def _generate_state_id(content: str) -> str:
        """Generate deterministic ID from content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class Trajectory:
    """Sequence of world states representing an execution trace."""
    states: List[WorldState]
    architecture_id: str  # Which agent architecture produced this
    task_id: str
    success: bool
    fitness_components: Dict[str, float] = field(default_factory=dict)

class WorldModelAbstractor:
    """Abstracts raw execution traces into comparable world states.

    The World Model is responsible for:
    1. Parsing raw agent logs/trajectories
    2. Categorizing steps (observation, action, outcome)
    3. Normalizing representations across different agent architectures
    4. Identifying causal boundaries between state transitions
    """

    def __init__(self, llm_client=None):
        """Initialize the World Model Abstractor.

        Args:
            llm_client: Optional LLM client for sophisticated state parsing.
                       If None, uses rule-based abstraction.
        """
        self.llm_client = llm_client
        self.state_normalizers: Dict[StateCategory, Any] = {}

    def abstract_trajectory(self, raw_trajectory: List[Dict[str, Any]]) -> Trajectory:
        """Convert a raw trajectory into an abstracted state sequence.

        Args:
            raw_trajectory: List of step dictionaries with keys like
                          'observation', 'action', 'result', 'error', etc.

        Returns:
            Trajectory with normalized WorldState objects
        """
        states = []

        for step in raw_trajectory:
            state = self._abstract_step(step)
            states.append(state)

        return Trajectory(
            states=states,
            architecture_id="unknown",  # To be set by caller
            task_id="unknown",
            success=self._assess_success(states)
        )

    def _abstract_step(self, step: Dict[str, Any]) -> WorldState:
        """Abstract a single step into a WorldState."""
        # Determine category
        if 'error' in step and step['error']:
            category = StateCategory.ERROR
            content = self._normalize_error(step['error'])
        elif 'result' in step:
            result = step['result']
            if self._is_successful(result):
                category = StateCategory.SUCCESS
            elif self._is_partial_success(result):
                category = StateCategory.PARTIAL_SUCCESS
            else:
                category = StateCategory.FAILURE
            content = self._normalize_result(result)
        elif 'action' in step:
            category = StateCategory.ACTION
            content = self._normalize_action(step['action'])
        else:
            category = StateCategory.OBSERVATION
            content = self._normalize_observation(step.get('observation', ''))

        metadata = {k: v for k, v in step.items() if k not in ['observation', 'action', 'result', 'error']}

        return WorldState(
            category=category,
            content=content,
            metadata=metadata
        )

    def _normalize_observation(self, obs: str) -> str:
        """Normalize observation text."""
        # Basic normalization: lowercase, strip whitespace
        return obs.strip().lower() if obs else ""

    def _normalize_action(self, action: Any) -> str:
        """Normalize action representation."""
        if isinstance(action, str):
            return action.strip().lower()
        elif isinstance(action, dict):
            # Normalize structured actions (tool calls, etc.)
            tool = action.get('tool', 'unknown')
            args = action.get('args', {})
            return f"{tool}:{args}"
        return str(action).strip().lower()

    def _normalize_result(self, result: Any) -> str:
        """Normalize result/outcome representation."""
        if isinstance(result, dict):
            # Extract key outcome indicators
            status = result.get('status', 'unknown')
            return f"status:{status}"
        return str(result).strip().lower()

    def _normalize_error(self, error: Any) -> str:
        """Normalize error representation."""
        if isinstance(error, dict):
            error_type = error.get('type', 'unknown')
            message = error.get('message', '')
            return f"{error_type}:{message}"
        return str(error).strip().lower()

    def _is_successful(self, result: Any) -> bool:
        """Determine if result indicates success."""
        if isinstance(result, dict):
            return result.get('status') in ['success', 'complete', 'ok']
        if isinstance(result, bool):
            return result
        return False

    def _is_partial_success(self, result: Any) -> bool:
        """Determine if result indicates partial success."""
        if isinstance(result, dict):
            return result.get('status') in ['partial', 'incomplete', 'retry']
        return False

    def _assess_success(self, states: List[WorldState]) -> bool:
        """Determine overall trajectory success."""
        # If final state is SUCCESS, trajectory succeeded
        if states and states[-1].category == StateCategory.SUCCESS:
            return True
        # If any state is ERROR, trajectory failed
        if any(s.category == StateCategory.ERROR for s in states):
            return False
        return False

    def compare_trajectories(self, traj1: Trajectory, traj2: Trajectory) -> float:
        """Compute similarity between two trajectories (0.0-1.0).

        Used by CKSE to determine if different architectures are solving
        the same problem in similar ways.
        """
        if len(traj1.states) == 0 or len(traj2.states) == 0:
            return 0.0

        # Simple sequence alignment based on state categories and content
        matches = 0
        total = max(len(traj1.states), len(traj2.states))

        for s1, s2 in zip(traj1.states, traj2.states):
            if s1.category == s2.category:
                # Content similarity (simple string equality for now)
                if s1.content == s2.content:
                    matches += 1
                elif self._content_similarity(s1.content, s2.content) > 0.8:
                    matches += 0.5

        return matches / total

    def _content_similarity(self, c1: str, c2: str) -> float:
        """Compute content similarity (basic implementation)."""
        if not c1 or not c2:
            return 0.0
        # Simple character overlap ratio
        set1, set2 = set(c1), set(c2)
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
