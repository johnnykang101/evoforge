"""
EvoForge Core - Convergent Knowledge Synthesis Engine (CKSE).

Extracts cross-architectural insights from execution traces to guide evolution.
Performs: Trace → World Model → Causal Reader → Synthesis → Knowledge Units.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from enum import Enum

from .world_model import WorldModel, WorldState
from .base import ExecutionResult


class KnowledgeType(Enum):
    """Types of knowledge extracted from traces."""
    CAUSAL = "causal"  # If X then Y relationships
    CORRELATIONAL = "correlational"  # Statistical associations
    PROCEDURAL = "procedural"  # How-to patterns
    CONSTRAINTS = "constraints"  # What doesn't work
    OPTIMIZATION = "optimization"  # Performance improvements


@dataclass
class KnowledgeUnit:
    """
    A synthesized unit of cross-architectural knowledge.
    Encapsulates an insight that can guide future mutations.
    """
    id: str
    type: KnowledgeType
    source_genome_ids: List[str]  # Architectures this knowledge came from
    supporting_traces: List[Dict[str, Any]]  # Evidence traces
    abstraction: str  # Generalized pattern (e.g., "Adding feedback loop improves success_rate by 15%")
    confidence: float  # 0-1 based on evidence strength
    applicable_architectures: Set[str] = field(default_factory=set)  # Module types it applies to
    fitness_impact: Optional[float] = None  # Measured delta if known
    created_timestamp: datetime = field(default_factory=datetime.now)
    citation_count: int = 0  # How many times used in mutations
    source_keywords: Set[str] = field(default_factory=set)  # Keywords from source insights for semantic matching

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source_genome_ids": self.source_genome_ids,
            "abstraction": self.abstraction,
            "confidence": self.confidence,
            "applicable_architectures": list(self.applicable_architectures),
            "fitness_impact": self.fitness_impact,
            "citation_count": self.citation_count,
            "source_keywords": list(self.source_keywords),
            "created_timestamp": self.created_timestamp.isoformat()
        }

    def is_applicable_to(self, genome: 'AgentGenome') -> bool:
        """Check if this knowledge could apply to a given architecture."""
        if not self.applicable_architectures:
            return True  # Universal knowledge
        genome_module_types = {m.type.value for m in genome.modules}
        return bool(self.applicable_architectures & genome_module_types)


class CausalReader:
    """
    Extracts causal and procedural knowledge from execution traces.
    Uses pattern matching and statistical analysis to infer "why" things worked.
    """

    def __init__(self, world_model: WorldModel):
        self.world_model = world_model

    def extract_knowledge(
        self,
        trace: List[Dict[str, Any]],
        context: Dict[str, Any],
        genome: 'AgentGenome'
    ) -> List[Dict[str, Any]]:
        """
        Analyze a trace and extract knowledge fragments.

        Returns:
            List of knowledge dicts with type, content, and confidence
        """
        insights = []

        # 1. Success/failure pattern analysis
        success_rate = sum(1 for e in trace if e.get("success", False)) / max(len(trace), 1)
        if success_rate > 0.8:
            insights.append({
                "type": KnowledgeType.OPTIMIZATION,
                "content": f"High success rate ({success_rate:.1%}) achieved",
                "confidence": min(success_rate, 0.95),
                "module": self._identify_key_module(trace)
            })
        elif success_rate < 0.3:
            insights.append({
                "type": KnowledgeType.CONSTRAINTS,
                "content": f"Low success rate ({success_rate:.1%}) indicates architectural issue",
                "confidence": 0.8,
                "module": self._identify_bottleneck(trace)
            })

        # 2. Module sequencing patterns
        seq_pattern = self._extract_sequence_pattern(trace)
        if seq_pattern:
            insights.append({
                "type": KnowledgeType.PROCEDURAL,
                "content": f"Effective sequence: {seq_pattern}",
                "confidence": 0.7,
                "pattern": seq_pattern
            })

        # 3. Error correlation analysis
        error_patterns = self._analyze_error_patterns(trace)
        for pattern, freq in error_patterns.items():
            if freq > 0.3:  # Occurs in >30% of steps
                insights.append({
                    "type": KnowledgeType.CAUSAL,
                    "content": f"Error '{pattern}' frequently follows {self._find_preceding_context(trace, pattern)}",
                    "confidence": min(freq, 0.9)
                })

        # 4. Latency hotspots
        slow_steps = self._find_slow_steps(trace)
        for step in slow_steps:
            insights.append({
                "type": KnowledgeType.OPTIMIZATION,
                "content": f"Module {step['module']} has high latency ({step['duration']:.2f}s)",
                "confidence": 0.85,
                "module": step["module"]
            })

        return insights

    def _identify_key_module(self, trace: List[Dict[str, Any]]) -> str:
        """Identify the module most associated with success."""
        module_success = {}
        for entry in trace:
            module = entry.get("module", "unknown")
            success = entry.get("success", False)
            if module not in module_success:
                module_success[module] = {"success": 0, "total": 0}
            module_success[module]["total"] += 1
            if success:
                module_success[module]["success"] += 1

        if not module_success:
            return "unknown"

        # Return module with highest success rate (min 5 executions)
        best = None
        best_rate = 0.0
        for module, stats in module_success.items():
            if stats["total"] >= 5:
                rate = stats["success"] / stats["total"]
                if rate > best_rate:
                    best_rate = rate
                    best = module
        return best or "unknown"

    def _identify_bottleneck(self, trace: List[Dict[str, Any]]) -> str:
        """Identify module causing most failures."""
        module_failures = {}
        for entry in trace:
            if not entry.get("success", True):
                module = entry.get("module", "unknown")
                module_failures[module] = module_failures.get(module, 0) + 1

        if not module_failures:
            return "unknown"
        return max(module_failures, key=module_failures.get)

    def _extract_sequence_pattern(self, trace: List[Dict[str, Any]]) -> Optional[str]:
        """Extract common module sequence pattern."""
        if len(trace) < 3:
            return None

        # Get module sequence
        seq = [entry.get("module", "?") for entry in trace]
        # Simple pattern: most common bigram
        bigrams = [(seq[i], seq[i+1]) for i in range(len(seq)-1)]
        if not bigrams:
            return None

        from collections import Counter
        common = Counter(bigrams).most_common(1)[0]
        return f"{common[0][0]} → {common[0][1]} (x{common[1]})"

    def _analyze_error_patterns(self, trace: List[Dict[str, Any]]) -> Dict[str, float]:
        """Find error types that co-occur with specific modules."""
        errors_by_module = {}
        for entry in trace:
            if entry.get("error"):
                module = entry.get("module", "unknown")
                error = str(entry["error"])[:50]  # Truncate
                key = f"{module}:{error}"
                errors_by_module[key] = errors_by_module.get(key, 0) + 1

        total_steps = len(trace)
        return {k: count/total_steps for k, count in errors_by_module.items()}

    def _find_slow_steps(self, trace: List[Dict[str, Any]], threshold: float = 5.0) -> List[Dict[str, Any]]:
        """Identify abnormally slow execution steps."""
        slow = []
        for entry in trace:
            duration = entry.get("duration", 0)
            if duration > threshold:
                slow.append({
                    "module": entry.get("module", "unknown"),
                    "duration": duration,
                    "step": entry.get("step_id")
                })
        return slow

    def _find_preceding_context(self, trace: List[Dict[str, Any]], error_pattern: str, window: int = 2) -> str:
        """Find what typically precedes an error."""
        # Simplified: return common preceding module
        error_indices = [i for i, e in enumerate(trace) if str(e.get("error", "")) in error_pattern]
        if not error_indices:
            return "unknown context"

        preceding = []
        for idx in error_indices:
            if idx > 0:
                for i in range(max(0, idx-window), idx):
                    preceding.append(trace[i].get("module", "?"))
        if not preceding:
            return "start of execution"

        from collections import Counter
        common = Counter(preceding).most_common(1)[0]
        return f"module '{common[0]}'"


class KnowledgeSynthesizer:
    """
    Combines insights from multiple traces across different architectures
    to produce generalized, cross-architectural knowledge units.
    """

    def __init__(self):
        self.knowledge_store: List[KnowledgeUnit] = []
        self.abstraction_cache: Dict[str, KnowledgeUnit] = {}  # Deduplicate by abstraction hash
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def synthesize(
        self,
        traces_and_genomes: List[Tuple[List[Dict[str, Any]], Dict[str, Any], 'AgentGenome']],
        causal_reader: CausalReader
    ) -> List[KnowledgeUnit]:
        """
        Synthesize knowledge from multiple execution traces.

        Args:
            traces_and_genomes: List of (trace, context, genome) tuples
            causal_reader: CausalReader for extracting raw insights

        Returns:
            List of new KnowledgeUnit objects
        """
        all_insights = []

        # Extract raw insights from each trace
        for trace, context, genome in traces_and_genomes:
            insights = causal_reader.extract_knowledge(trace, context, genome)
            for insight in insights:
                insight["source_genome_id"] = genome.id
                insight["source_genome_name"] = genome.name
                all_insights.append(insight)

        # Cluster and abstract insights
        clustered = self._cluster_similar_insights(all_insights)

        # Create knowledge units (with semantic cache lookup)
        new_units = []
        for cluster in clustered:
            # Try semantic lookup against existing knowledge first
            existing = self._semantic_lookup(cluster)
            if existing:
                # Cache hit: reuse existing unit, update citation count
                existing.citation_count += 1
                self._cache_hits += 1
            else:
                # Cache miss: create new unit
                unit = self._create_knowledge_unit(cluster)
                if unit is None:
                    # Abstraction hash matched existing entry — count as cache hit
                    self._cache_hits += 1
                else:
                    new_units.append(unit)
                    # Add to store immediately so subsequent clusters can match
                    self.knowledge_store.append(unit)
                    self._cache_misses += 1

        return new_units

    def _cluster_similar_insights(self, insights: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group insights by semantic similarity."""
        clusters = []
        unassigned = insights.copy()

        while unassigned:
            seed = unassigned.pop(0)
            cluster = [seed]

            # Find similar insights
            to_remove = []
            for other in unassigned:
                if self._insights_match(seed, other):
                    cluster.append(other)
                    to_remove.append(other)

            for item in to_remove:
                unassigned.remove(item)

            clusters.append(cluster)

        return clusters

    def _insights_match(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Check if two insights are semantically similar."""
        if a["type"] != b["type"]:
            return False

        # Simple keyword matching (could use embeddings for better matching)
        content_a = a["content"].lower()
        content_b = b["content"].lower()

        # Check for shared keywords
        words_a = set(content_a.split())
        words_b = set(content_b.split())
        overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)

        return overlap > 0.3  # 30% word overlap threshold

    def _create_knowledge_unit(self, cluster: List[Dict[str, Any]]) -> Optional[KnowledgeUnit]:
        """Convert a cluster of insights into a KnowledgeUnit."""
        if not cluster:
            return None

        # Deduplicate by abstraction hash
        abstraction = self._generate_abstraction(cluster)
        abstraction_hash = hashlib.md5(abstraction.encode()).hexdigest()[:16]

        if abstraction_hash in self.abstraction_cache:
            return None  # Already have this knowledge (hash dedup)

        # Extract sources
        source_genome_ids = [insight["source_genome_id"] for insight in cluster]

        # Determine applicable architectures from modules mentioned
        applicable = set()
        for insight in cluster:
            if "module" in insight and insight["module"] != "unknown":
                applicable.add(insight["module"])

        # Collect source keywords from all insights for semantic matching
        source_keywords = set()
        for insight in cluster:
            source_keywords.update(insight.get("content", "").lower().split())

        # Compute confidence as weighted average
        confidences = [insight["confidence"] for insight in cluster]
        avg_confidence = sum(confidences) / len(confidences)

        unit = KnowledgeUnit(
            id=abstraction_hash,
            type=cluster[0]["type"],
            source_genome_ids=source_genome_ids,
            supporting_traces=[],  # Could store references
            abstraction=abstraction,
            confidence=avg_confidence,
            applicable_architectures=applicable,
            source_keywords=source_keywords,
        )

        self.abstraction_cache[abstraction_hash] = unit
        return unit

    def _semantic_lookup(self, cluster: List[Dict[str, Any]], threshold: float = 0.4) -> Optional[KnowledgeUnit]:
        """Check if a cluster matches an existing knowledge unit semantically.

        Uses word-overlap similarity against stored abstractions.
        Returns the matching unit if found, None otherwise.
        """
        if not self.knowledge_store or not cluster:
            return None

        # Build representative content from cluster
        cluster_words = set()
        for insight in cluster:
            cluster_words.update(insight.get("content", "").lower().split())

        if not cluster_words:
            return None

        # Check against existing knowledge units using both abstraction and source keywords
        best_match = None
        best_score = 0.0
        for unit in self.knowledge_store:
            # Combine abstraction words and stored source keywords for matching
            unit_words = set(unit.abstraction.lower().split()) | unit.source_keywords
            if not unit_words:
                continue
            overlap = len(cluster_words & unit_words) / max(len(cluster_words | unit_words), 1)
            if overlap > best_score:
                best_score = overlap
                best_match = unit

        if best_score >= threshold:
            return best_match
        return None

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get knowledge cache statistics."""
        total = self._cache_hits + self._cache_misses
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / total if total > 0 else 0.0,
            "knowledge_store_size": len(self.knowledge_store),
            "abstraction_cache_size": len(self.abstraction_cache),
        }

    def _generate_abstraction(self, cluster: List[Dict[str, Any]]) -> str:
        """Generate a generalized statement from similar insights."""
        # Simplified: take the longest/most detailed content
        cluster.sort(key=lambda x: len(x["content"]), reverse=True)
        base = cluster[0]["content"]

        # Add specificity from cluster
        for insight in cluster[1:min(3, len(cluster))]:
            if insight["confidence"] > 0.8:
                base += f" (also observed: {insight['content'][:80]}...)"

        return base


class KnowledgeGenomeAnnotator:
    """
    Translates knowledge units into genome parameter adjustments.
    Provides guidance for mutation operators.
    """

    def __init__(self, knowledge_synthesizer: KnowledgeSynthesizer):
        self.synthesizer = knowledge_synthesizer

    def generate_mutation_hints(
        self,
        genome: 'AgentGenome',
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate mutation hints based on applicable knowledge.

        Returns:
            List of mutation suggestions with target, action, and confidence
        """
        applicable_knowledge = [
            k for k in self.synthesizer.knowledge_store
            if k.is_applicable_to(genome) and k.confidence > 0.6
        ]

        # Sort by confidence and recency
        applicable_knowledge.sort(key=lambda k: (k.confidence, k.citation_count), reverse=True)

        hints = []
        for knowledge in applicable_knowledge[:top_k]:
            hint = self._convert_to_mutation_hint(knowledge, genome)
            if hint:
                hints.append(hint)

        return hints

    def _convert_to_mutation_hint(self, knowledge: KnowledgeUnit, genome: 'AgentGenome') -> Optional[Dict[str, Any]]:
        """Convert a knowledge unit into a concrete mutation suggestion."""
        abstraction = knowledge.abstraction.lower()

        # Pattern matching on abstraction text
        if "success rate" in abstraction or "improves" in abstraction:
            # Suggests increasing exploration or adding feedback loops
            return {
                "strategy": "increase_exploration",
                "target_modules": [m.id for m in genome.modules if m.type.value in ["planner", "selector"]],
                "action": "adjust_parameters",
                "parameters": {"temperature": "+0.2", "max_steps": "+2"},
                "confidence": knowledge.confidence,
                "knowledge_id": knowledge.id
            }

        elif "latency" in abstraction or "slow" in abstraction:
            # Suggests optimizing timeout/retry parameters
            return {
                "strategy": "optimize_performance",
                "target_modules": [m.id for m in genome.modules if m.type.value in ["executor", "evaluator"]],
                "action": "adjust_parameters",
                "parameters": {"timeout": "-20%", "max_retries": "no_change"},
                "confidence": knowledge.confidence,
                "knowledge_id": knowledge.id
            }

        elif "error" in abstraction or "failure" in abstraction:
            # Suggests adding error handling or reconfiguration
            return {
                "strategy": "increase_robustness",
                "target_modules": [m.id for m in genome.modules],
                "action": "add_validation",
                "parameters": {"max_retries": "+1"},
                "confidence": knowledge.confidence,
                "knowledge_id": knowledge.id
            }

        elif "sequence" in abstraction or "order" in abstraction:
            # Suggests connection topology changes
            return {
                "strategy": "reorder_connections",
                "action": "mutate_topology",
                "confidence": knowledge.confidence,
                "knowledge_id": knowledge.id
            }

        return None


class ConvergentKnowledgeSynthesisEngine:
    """
    Main CKSE orchestrator. Integrates World Model, Causal Reader, and Synthesis.

    Workflow:
        Execution Traces → World States → Causal Insights → Cross-arch Synthesis
           ↓
        Knowledge Units → Genome Annotations → Guided Mutations
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.world_model = WorldModel()
        self.causal_reader = CausalReader(self.world_model)
        self.synthesizer = KnowledgeSynthesizer()
        self.annotator = KnowledgeGenomeAnnotator(self.synthesizer)
        self.storage_path = storage_path

    def process_traces(
        self,
        traces_batch: List[Tuple[List[Dict[str, Any]], Dict[str, Any], 'AgentGenome']]
    ) -> List[KnowledgeUnit]:
        """
        Process a batch of execution traces and synthesize knowledge.

        Args:
            traces_batch: List of (trace, context, genome) tuples from recent executions

        Returns:
            Newly synthesized knowledge units
        """
        # 1. Abstract traces into world states (handled by synthesizer)
        # 2. Extract causal insights
        # 3. Synthesize cross-architectural knowledge
        new_units = self.synthesizer.synthesize(traces_batch, self.causal_reader)

        # Persist if storage path configured
        if self.storage_path:
            self._persist_knowledge()

        return new_units

    def get_mutation_hints(
        self,
        genome: 'AgentGenome',
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get knowledge-guided mutation suggestions for a genome.

        Args:
            genome: Target genome to mutate
            context: Optional execution context

        Returns:
            List of mutation hints ordered by priority
        """
        return self.annotator.generate_mutation_hints(genome)

    def get_applicable_knowledge(
        self,
        genome: 'AgentGenome',
        min_confidence: float = 0.7
    ) -> List[KnowledgeUnit]:
        """Retrieve knowledge units applicable to this genome."""
        applicable = [
            k for k in self.synthesizer.knowledge_store
            if k.is_applicable_to(genome) and k.confidence >= min_confidence
        ]
        applicable.sort(key=lambda k: k.confidence, reverse=True)
        return applicable

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get aggregate cache statistics from the CKSE pipeline."""
        return self.synthesizer.get_cache_stats()

    def _persist_knowledge(self):
        """Save knowledge store to disk."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)

        knowledge_file = os.path.join(self.storage_path, "knowledge_units.json")
        data = {
            "units": [k.to_dict() for k in self.synthesizer.knowledge_store],
            "timestamp": datetime.now().isoformat()
        }
        with open(knowledge_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_knowledge(self, path: str) -> None:
        """Load knowledge store from disk."""
        with open(path, 'r') as f:
            data = json.load(f)

        self.synthesizer.knowledge_store = []
        for unit_data in data.get("units", []):
            unit = KnowledgeUnit(
                id=unit_data["id"],
                type=KnowledgeType(unit_data["type"]),
                source_genome_ids=unit_data["source_genome_ids"],
                supporting_traces=[],
                abstraction=unit_data["abstraction"],
                confidence=unit_data["confidence"],
                applicable_architectures=set(unit_data["applicable_architectures"]),
                citation_count=unit_data.get("citation_count", 0),
                source_keywords=set(unit_data.get("source_keywords", [])),
                created_timestamp=datetime.fromisoformat(unit_data["timestamp"])
            )
            self.synthesizer.knowledge_store.append(unit)
            self.synthesizer.abstraction_cache[unit.id] = unit
