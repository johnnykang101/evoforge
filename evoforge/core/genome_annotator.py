"""Genome Annotator.

Maps knowledge units to tunable architecture genome parameters.
Converts abstract knowledge into concrete architectural modifications.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from evoforge.core.synthesizer import KnowledgeUnit
from evoforge.evolution.genome import ArchitectureGenome

@dataclass
class Annotation:
    """A specific genome modification derived from knowledge."""
    parameter_path: str  # e.g., "memory.strategy"
    suggested_value: Any
    knowledge_id: str
    confidence: float
    rationale: str

class GenomeAnnotator:
    """Maps KnowledgeUnits to concrete genome parameter suggestions.

    The Genome Annotator is the bridge between abstract knowledge and
    concrete architectural changes. It translates statements like:
      "When using ReAct with large context, summary compression helps"
    Into specific genome annotations:
      {"memory.compression_strategy": "summarize", "confidence": 0.8}

    Uses LLM-based interpretation or rule-based mapping.
    """

    def __init__(self):
        self.annotation_templates: Dict[str, Dict[str, Any]] = {}
        self.parameter_schema: Dict[str, Any] = {}

    def annotate_genome(self, genome: ArchitectureGenome, knowledge_units: List[KnowledgeUnit]) -> List[Annotation]:
        """Generate annotations for a genome based on knowledge units.

        Args:
            genome: The genome to annotate
            knowledge_units: Relevant knowledge units

        Returns:
            List of Annotation objects suggesting parameter changes
        """
        annotations = []

        for unit in knowledge_units:
            if unit.confidence < 0.5:
                continue  # Skip low-confidence knowledge

            # Parse the knowledge statement and map to genome parameters
            unit_annotations = self._interpret_knowledge(unit, genome)
            annotations.extend(unit_annotations)

        return annotations

    def _interpret_knowledge(self, unit: KnowledgeUnit, genome: ArchitectureGenome) -> List[Annotation]:
        """Interpret a knowledge unit and produce genome annotations."""
        annotations = []

        # Rule-based mapping from knowledge patterns to parameters
        statement = unit.statement.lower()

        # Pattern: planning algorithm recommendations
        if 'react' in statement or 'chain-of-thought' in statement or 'tree-of-thought' in statement:
            if 'summary' in statement or 'compression' in statement:
                annotations.append(Annotation(
                    parameter_path="memory.compression_strategy",
                    suggested_value="summarize",
                    knowledge_id=unit.id,
                    confidence=unit.confidence * 0.9,
                    rationale=f"Knowledge suggests summary compression based on: {unit.statement}"
                ))

        # Pattern: memory-related guidance
        if 'memory' in statement or 'context' in statement:
            if 'vector' in statement:
                annotations.append(Annotation(
                    parameter_path="memory.strategy",
                    suggested_value="vector_db",
                    knowledge_id=unit.id,
                    confidence=unit.confidence * 0.8,
                    rationale=unit.statement
                ))
            elif 'graph' in statement:
                annotations.append(Annotation(
                    parameter_path="memory.strategy",
                    suggested_value="graph",
                    knowledge_id=unit.id,
                    confidence=unit.confidence * 0.8,
                    rationale=unit.statement
                ))

        # Pattern: tool selection
        if 'tool' in statement or 'function' in statement:
            # Could suggest tool selection policy parameters
            pass

        # Pattern: learning rate / optimization
        if 'learning' in statement or 'optimization' in statement or 'grpo' in statement:
            if 'stable' in statement or 'stable' in statement:
                annotations.append(Annotation(
                    parameter_path="optimization.stable",
                    suggested_value=True,
                    knowledge_id=unit.id,
                    confidence=unit.confidence * 0.85,
                    rationale=unit.statement
                ))

        return annotations

    def apply_annotations(self, genome: ArchitectureGenome, annotations: List[Annotation]) -> ArchitectureGenome:
        """Apply annotations to modify genome parameters.

        Args:
            genome: Original genome
            annotations: List of annotations to apply

        Returns:
            Modified genome (new instance)
        """
        # Create a copy
        new_config = genome.config.copy()

        for ann in annotations:
            # Navigate to parameter using dot notation
            parts = ann.parameter_path.split('.')
            current = new_config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = ann.suggested_value

        return ArchitectureGenome(config=new_config)

    def get_annotation_confidence(self, annotations: List[Annotation]) -> float:
        """Compute overall confidence in a set of annotations."""
        if not annotations:
            return 0.0
        return sum(a.confidence for a in annotations) / len(annotations)
