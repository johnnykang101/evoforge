"""Causal Reader.

Extracts causal relationships and procedural knowledge from trajectories.
Answers: "Why did this work?" and "Why did this fail?"
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from evoforge.core.world_model import WorldState, Trajectory, TrajectoryState, StateCategory

@dataclass
class CausalInsight:
    """Extracted causal relationship."""
    cause: str
    effect: str
    confidence: float  # 0.0-1.0
    supporting_trajectories: List[str]  # task_ids
    architecture_context: str

class CausalReader:
    """Extracts causal insights from execution trajectories.

    The Causal Reader analyzes trajectories to answer:
    - Which actions led to success?
    - Which patterns preceded failures?
    - What are the key decision points?
    - How do architectural choices influence outcomes?

    Uses LLM-based analysis to infer causal chains.
    """

    def __init__(self, llm_client=None):
        """Initialize Causal Reader.

        Args:
            llm_client: LLM client for sophisticated causal inference.
                       If None, uses pattern-matching heuristics.
        """
        self.llm_client = llm_client
        self.insight_cache: List[CausalInsight] = []

    def extract_insights(self, trajectory: Trajectory) -> List[CausalInsight]:
        """Extract all causal insights from a single trajectory.

        Args:
            trajectory: The trajectory to analyze

        Returns:
            List of CausalInsight objects
        """
        insights = []

        if self.llm_client:
            insights.extend(self._llm_extract(trajectory))
        else:
            insights.extend(self._heuristic_extract(trajectory))

        # Tag insights with architecture context
        for insight in insights:
            insight.architecture_context = trajectory.architecture_id

        return insights

    def _heuristic_extract(self, trajectory: Trajectory) -> List[CausalInsight]:
        """Extract insights using pattern-matching heuristics."""
        insights = []

        states = trajectory.states
        for i in range(len(states) - 1):
            current = states[i]
            next_state = states[i + 1]

            # Look for transition patterns
            if current.category == StateCategory.ACTION and next_state.category == StateCategory.SUCCESS:
                insight = CausalInsight(
                    cause=f"action:{current.content}",
                    effect=f"success:{next_state.content}",
                    confidence=0.7,
                    supporting_trajectories=[trajectory.task_id],
                    architecture_context=""
                )
                insights.append(insight)

            if current.category == StateCategory.ACTION and next_state.category == StateCategory.ERROR:
                insight = CausalInsight(
                    cause=f"action:{current.content}",
                    effect=f"error:{next_state.content}",
                    confidence=0.8,
                    supporting_trajectories=[trajectory.task_id],
                    architecture_context=""
                )
                insights.append(insight)

        return insights

    def _llm_extract(self, trajectory: Trajectory) -> List[CausalInsight]:
        """Extract insights using LLM-based causal inference."""
        # Placeholder for LLM integration
        # Expected: Call LLM with trajectory, parse structured response
        return []

    def extract_cross_architecture_patterns(self, trajectories: List[Trajectory]) -> List[CausalInsight]:
        """Identify causal patterns that hold across multiple architectures.

        This is CKSE's key capability: learning about architectures from
        observations of many different architecture configurations.
        """
        cross_patterns = []

        # Group trajectories by architecture
        by_arch: Dict[str, List[Trajectory]] = {}
        for traj in trajectories:
            by_arch.setdefault(traj.architecture_id, []).append(traj)

        # For each architecture, extract insights
        all_insights: List[CausalInsight] = []
        for arch_trajs in by_arch.values():
            for traj in arch_trajs:
                all_insights.extend(self.extract_insights(traj))

        # Identify patterns that appear in multiple architectures
        # Group by causal relationship (ignoring architecture)
        pattern_groups: Dict[Tuple[str, str], List[CausalInsight]] = {}
        for insight in all_insights:
            key = (insight.cause, insight.effect)
            pattern_groups.setdefault(key, []).append(insight)

        # Patterns observed across different architectures are more robust
        for key, insights in pattern_groups.items():
            architectures = set(i.architecture_context for i in insights)
            if len(architectures) >= 2:
                # Weighted confidence based on number of architectures
                avg_confidence = sum(i.confidence for i in insights) / len(insights)
                cross_insight = CausalInsight(
                    cause=key[0],
                    effect=key[1],
                    confidence=avg_confidence * min(1.0, len(architectures) / 3),
                    supporting_trajectories=[t for i in insights for t in i.supporting_trajectories],
                    architecture_context="cross-architecture"
                )
                cross_patterns.append(cross_insight)

        return cross_patterns

    def get_insights_for_architecture(self, architecture_id: str) -> List[CausalInsight]:
        """Retrieve all insights relevant to a specific architecture."""
        return [i for i in self.insight_cache if i.architecture_context == architecture_id]
