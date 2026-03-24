"""Knowledge Synthesis Engine.

Combines causal insights into composite knowledge units.
Performs cross-architecture generalization and validation.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from evoforge.core.causal_reader import CausalInsight
from evoforge.core.world_model import Trajectory

@dataclass
class KnowledgeUnit:
    """A synthesized unit of knowledge."""
    id: str
    statement: str  # Natural language description of the knowledge
    supporting_insights: List[CausalInsight]
    cross_architecture: bool  # True if validated across architectures
    confidence: float
    applicable_architectures: List[str] = field(default_factory=list)
    counterexamples: List[str] = field(default_factory=list)  # contradicting cases
    metadata: Dict[str, Any] = field(default_factory=dict)

    def applies_to_architecture(self, architecture_id: str) -> bool:
        """Check if this knowledge is applicable to given architecture."""
        if self.cross_architecture:
            return True
        return architecture_id in self.applicable_architectures

class KnowledgeSynthesizer:
    """Synthesizes knowledge units from causal insights.

    The Knowledge Synthesizer:
    1. Groups related causal insights
    2. Generalizes statements to be architecture-agnostic when possible
    3. Validates consistency across different agent architectures
    4. Produces KnowledgeUnits that can guide genome mutations
    """

    def __init__(self):
        self.knowledge_store: List[KnowledgeUnit] = []

    def synthesize(self, insights: List[CausalInsight]) -> List[KnowledgeUnit]:
        """Synthesize a set of insights into knowledge units.

        Args:
            insights: Causal insights to synthesize

        Returns:
            List of synthesized KnowledgeUnit objects
        """
        units = []

        # Group insights by causal relationship type
        groups = self._cluster_insights(insights)

        for group in groups:
            unit = self._create_knowledge_unit(group)
            units.append(unit)

        # Store synthesized units
        self.knowledge_store.extend(units)

        return units

    def _cluster_insights(self, insights: List[CausalInsight]) -> List[List[CausalInsight]]:
        """Cluster similar insights together."""
        clusters: List[List[CausalInsight]] = []

        for insight in insights:
            added = False
            for cluster in clusters:
                # Check if this insight is similar to cluster members
                representative = cluster[0]
                if self._insights_similar(insight, representative):
                    cluster.append(insight)
                    added = True
                    break
            if not added:
                clusters.append([insight])

        return clusters

    def _insights_similar(self, i1: CausalInsight, i2: CausalInsight, threshold: float = 0.7) -> bool:
        """Determine if two insights are semantically similar."""
        # Simple similarity based on (cause, effect) pair
        # In production, use embeddings for semantic similarity
        same_cause = i1.cause == i2.cause
        same_effect = i1.effect == i2.effect

        if same_cause and same_effect:
            return True

        # Check partial string overlap
        cause_sim = self._string_similarity(i1.cause, i2.cause)
        effect_sim = self._string_similarity(i1.effect, i2.effect)
        return (cause_sim + effect_sim) / 2 >= threshold

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Compute string similarity (0.0-1.0)."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        # Simple character-level Jaccard
        set1, set2 = set(s1), set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _create_knowledge_unit(self, cluster: List[CausalInsight]) -> KnowledgeUnit:
        """Create a KnowledgeUnit from a cluster of insights."""
        # Determine if cross-architecture
        architectures = set()
        for insight in cluster:
            architectures.update(insight.architecture_context.split(','))

        cross_arch = len(architectures) > 1

        # Generate statement from insights
        if cluster:
            exemplar = cluster[0]
            statement = f"When {exemplar.cause}, then {exemplar.effect}."
        else:
            statement = "Unknown pattern"

        # Calculate confidence (weighted by support and cross-arch validation)
        base_confidence = sum(i.confidence for i in cluster) / len(cluster)
        cross_arch_boost = 1.2 if cross_arch else 1.0
        confidence = min(1.0, base_confidence * cross_arch_boost)

        return KnowledgeUnit(
            id=self._generate_unit_id(cluster),
            statement=statement,
            supporting_insights=cluster,
            cross_architecture=cross_arch,
            confidence=confidence,
            applicable_architectures=list(architectures),
            counterexamples=[]
        )

    def _generate_unit_id(self, cluster: List[CausalInsight]) -> str:
        """Generate unique ID for knowledge unit."""
        import hashlib
        content = "_".join([f"{i.cause}->{i.effect}" for i in cluster[:3]])
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def validate_knowledge_unit(self, unit: KnowledgeUnit, test_trajectories: List[Trajectory]) -> bool:
        """Validate a knowledge unit against additional trajectories."""
        # For now, simple validation: check if knowledge holds in test trajectories
        # In production, use more sophisticated statistical validation
        return unit.confidence > 0.6  # Placeholder

    def get_applicable_knowledge(self, architecture_id: str, min_confidence: float = 0.5) -> List[KnowledgeUnit]:
        """Get all knowledge units applicable to a given architecture."""
        applicable = [
            u for u in self.knowledge_store
            if u.applies_to_architecture(architecture_id)
            and u.confidence >= min_confidence
        ]
        return sorted(applicable, key=lambda u: u.confidence, reverse=True)
