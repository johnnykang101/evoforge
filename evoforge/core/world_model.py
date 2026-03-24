"""
EvoForge Core - World Model (WM).
Abstracts raw execution traces into comparable state representations.
Used for fitness evaluation and novelty detection.
"""

from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
import hashlib
import json


@dataclass
class WorldState:
    """
    Abstract representation of an agent's state at a point in time.
    Used for comparing different execution trajectories.
    """
    features: Dict[str, float]  # Numerical features
    categorical: Dict[str, str]  # Categorical features
    context_hash: str  # Hash of the execution context
    timestamp: float

    def to_vector(self) -> List[float]:
        """Convert to a fixed-length feature vector for similarity computation."""
        # Sort keys for consistent ordering
        feature_keys = sorted(self.features.keys())
        values = [self.features[k] for k in feature_keys]

        # Include some categorical hashed values (simple approach)
        cat_hashes = []
        for key in sorted(self.categorical.keys()):
            val = self.categorical[key]
            # Simple hash to float in [0, 1]
            h = int(hashlib.md5(f"{key}:{val}".encode()).hexdigest()[:8], 16)
            cat_hashes.append(h / 2**32)

        return values + cat_hashes

    def distance_to(self, other: 'WorldState') -> float:
        """Compute Euclidean distance between two world states."""
        v1 = self.to_vector()
        v2 = other.to_vector()
        if len(v1) != len(v2):
            return float('inf')
        return sum((a - b) ** 2 for a, b in zip(v1, v2)) ** 0.5


class WorldModel:
    """
    The World Model abstracts raw execution traces into structured state representations.
    It provides:
    1. State abstraction from execution contexts
    2. Normalization and feature extraction
    3. State transition modeling (for predicting sequences)
    """

    def __init__(self, feature_config: Optional[Dict[str, Any]] = None):
        self.feature_config = feature_config or {
            "include_performance_metrics": True,
            "include_module_activations": True,
            "include_context_variables": True,
            "max_features": 50
        }
        self.state_history: List[WorldState] = []
        self.feature_extractors = self._initialize_extractors()

    def _initialize_extractors(self) -> Dict[str, Callable]:
        """Initialize feature extraction functions."""
        return {
            "success_rate": self._extract_success_rate,
            "step_count": self._extract_step_count,
            "module_diversity": self._extract_module_diversity,
            "execution_depth": self._extract_execution_depth,
            "error_rate": self._extract_error_rate,
            "throughput": self._extract_throughput
        }

    def abstract_trace(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> WorldState:
        """
        Convert a raw execution trace into a WorldState.
        The trace is a list of module execution records.
        """
        features = {}
        categorical = {}

        # Extract features using registered extractors
        for feature_name, extractor in self.feature_extractors.items():
            try:
                value = extractor(trace, context)
                if isinstance(value, (int, float)):
                    features[feature_name] = float(value)
                elif isinstance(value, str):
                    categorical[feature_name] = value
            except Exception:
                pass

        # Add custom context features
        if self.feature_config.get("include_context_variables", True):
            for key, value in context.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    features[f"context_{key}"] = float(value)
                elif isinstance(value, str):
                    categorical[f"context_{key}"] = value[:50]  # Truncate long strings

        # Normalize features to [0, 1] range using simple min-max (could use running stats)
        features = self._normalize_features(features)

        # Create context hash for grouping similar contexts
        context_hash = self._hash_context(context)

        state = WorldState(
            features=features,
            categorical=categorical,
            context_hash=context_hash,
            timestamp=__import__('time').time()
        )

        self.state_history.append(state)
        return state

    def _normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Apply min-max normalization to features."""
        # Simple static normalization ranges (could be learned from data)
        ranges = {
            "success_rate": (0, 1),
            "step_count": (0, 100),
            "module_diversity": (0, 10),
            "execution_depth": (0, 20),
            "error_rate": (0, 1),
            "throughput": (0, 100)
        }

        normalized = {}
        for key, value in features.items():
            min_val, max_val = ranges.get(key, (0, 1))
            if max_val > min_val:
                normalized[key] = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
            else:
                normalized[key] = 0.0
        return normalized

    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create a deterministic hash of the execution context."""
        # Sort keys for consistency
        sorted_items = sorted(context.items(), key=lambda x: str(x[0]))
        # Convert to string and hash
        ctx_str = json.dumps(sorted_items, sort_keys=True, default=str)
        return hashlib.md5(ctx_str.encode()).hexdigest()[:16]

    def get_similar_states(self, state: WorldState, k: int = 5) -> List[Tuple[WorldState, float]]:
        """
        Find k most similar world states from history.
        Returns list of (state, similarity_score) tuples.
        """
        if not self.state_history:
            return []

        distances = []
        for hist_state in self.state_history[-1000:]:  # Only check recent for efficiency
            dist = state.distance_to(hist_state)
            distances.append((hist_state, dist))

        # Sort by distance (ascending) and take top-k
        distances.sort(key=lambda x: x[1])
        return distances[:k]

    def compute_trajectory_distance(self, trace1: List[Dict[str, Any]], trace2: List[Dict[str, Any]],
                                   context1: Dict[str, Any], context2: Dict[str, Any]) -> float:
        """
        Compute distance between two execution trajectories.
        Uses dynamic time warping or simple state sequence comparison.
        """
        state1 = self.abstract_trace(trace1, context1)
        state2 = self.abstract_trace(trace2, context2)

        # For now, simple Euclidean distance between final states
        # Could be extended to DTW for full trajectory comparison
        return state1.distance_to(state2)

    # Feature extractors
    def _extract_success_rate(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        successes = sum(1 for entry in trace if entry.get("success", False))
        total = len(trace) if trace else 1
        return successes / total

    def _extract_step_count(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        return float(len(trace))

    def _extract_module_diversity(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        modules = set(entry.get("module", "unknown") for entry in trace)
        return float(len(modules))

    def _extract_execution_depth(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        # Estimate recursion or nesting depth
        max_nesting = 0
        current_nesting = 0
        for entry in trace:
            if entry.get("type") == "subtask_start":
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif entry.get("type") == "subtask_end":
                current_nesting = max(0, current_nesting - 1)
        return float(max_nesting)

    def _extract_error_rate(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        errors = sum(1 for entry in trace if entry.get("error") is not None)
        total = len(trace) if trace else 1
        return errors / total

    def _extract_throughput(self, trace: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        """Tasks per unit time (approximated)."""
        if not trace:
            return 0.0
        start_time = trace[0].get("timestamp", 0)
        end_time = trace[-1].get("timestamp", 1)
        duration = max(end_time - start_time, 0.001)
        return len(trace) / duration

    def clear_history(self):
        """Clear state history (useful for context-mode to manage memory)."""
        self.state_history = []


class StateCategory:
    """Categories for trajectory states used by CausalReader."""
    ACTION = "action"
    SUCCESS = "success"
    ERROR = "error"
    OBSERVATION = "observation"
    DECISION = "decision"


@dataclass
class TrajectoryState:
    """A single state in a trajectory."""
    category: str  # One of StateCategory values
    content: str
    timestamp: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Trajectory:
    """A sequence of states from an agent execution.

    Used by CausalReader to extract causal insights.
    """
    task_id: str
    architecture_id: str
    states: List[TrajectoryState]
    outcome: Optional[str] = None
    fitness: Optional[float] = None
