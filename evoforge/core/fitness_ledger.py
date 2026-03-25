"""FitnessLedger — persistent genome evaluation cache.

Prevents redundant evaluation by storing genome outcome history keyed on a
content-addressable genome hash.  Pairs with TokenCache: Ledger deduplicates
whole-genome evaluations; TokenCache deduplicates LLM calls within evals.

Expected ROI: 40-60% reduction in redundant genome evaluations.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from evoforge.evolution.genome import ArchitectureGenome

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Genome hashing helper
# ---------------------------------------------------------------------------

def compute_genome_hash(genome: "ArchitectureGenome") -> str:
    """Return a 16-char hex content-addressable hash for *genome*.

    Uses SHA-256 over the canonical JSON representation of ``genome.config``
    so that two genomes with identical configs always collide.
    """
    canonical = json.dumps(genome.config, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LedgerEntry:
    """Record of a genome evaluation outcome."""

    genome_hash: str
    best_score: float
    timestamp: str
    parent_genome_hash: str = ""
    mutation_applied: str = ""
    battery_scores: Dict[str, float] = field(default_factory=dict)
    pareto_metrics: Dict[str, float] = field(default_factory=dict)
    evaluation_count: int = 1

    def to_dict(self) -> dict:
        return {
            "genome_hash": self.genome_hash,
            "best_score": self.best_score,
            "timestamp": self.timestamp,
            "parent_genome_hash": self.parent_genome_hash,
            "mutation_applied": self.mutation_applied,
            "battery_scores": self.battery_scores,
            "pareto_metrics": self.pareto_metrics,
            "evaluation_count": self.evaluation_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LedgerEntry":
        return cls(
            genome_hash=data["genome_hash"],
            best_score=data["best_score"],
            timestamp=data["timestamp"],
            parent_genome_hash=data.get("parent_genome_hash", ""),
            mutation_applied=data.get("mutation_applied", ""),
            battery_scores=data.get("battery_scores", {}),
            pareto_metrics=data.get("pareto_metrics", {}),
            evaluation_count=data.get("evaluation_count", 1),
        )


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

class FitnessLedger:
    """Persistent genome outcome history.

    Usage::

        ledger = FitnessLedger()
        metrics = evaluator.evaluate_genome(genome, ledger=ledger)
        ledger.save("evolution.ledger.json")

        # Next run:
        ledger = FitnessLedger()
        ledger.load("evolution.ledger.json")
        metrics = evaluator.evaluate_genome(genome, ledger=ledger)  # cache hit
    """

    def __init__(self) -> None:
        self._store: Dict[str, LedgerEntry] = {}
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Core cache API
    # ------------------------------------------------------------------

    def lookup(self, genome_hash: str) -> Optional[LedgerEntry]:
        """Return a cached ``LedgerEntry`` on hit, or ``None`` on miss."""
        entry = self._store.get(genome_hash)
        if entry is not None:
            self._hits += 1
            logger.debug("Ledger hit: %s (score=%.4f)", genome_hash, entry.best_score)
            return entry
        self._misses += 1
        return None

    def record(
        self,
        genome_hash: str,
        best_score: float,
        *,
        parent_genome_hash: str = "",
        mutation_applied: str = "",
        battery_scores: Optional[Dict[str, float]] = None,
        pareto_metrics: Optional[Dict[str, float]] = None,
    ) -> LedgerEntry:
        """Record or update the evaluation result for *genome_hash*.

        If an entry already exists, increments ``evaluation_count`` and
        updates ``best_score`` only when the new score improves on the old.
        """
        now = datetime.now(timezone.utc).isoformat()
        existing = self._store.get(genome_hash)
        if existing is not None:
            existing.evaluation_count += 1
            if best_score > existing.best_score:
                existing.best_score = best_score
                existing.timestamp = now
            return existing

        entry = LedgerEntry(
            genome_hash=genome_hash,
            best_score=best_score,
            timestamp=now,
            parent_genome_hash=parent_genome_hash,
            mutation_applied=mutation_applied,
            battery_scores=battery_scores or {},
            pareto_metrics=pareto_metrics or {},
        )
        self._store[genome_hash] = entry
        return entry

    def get_lineage(self, genome_hash: str) -> List[LedgerEntry]:
        """Walk the parent chain from *genome_hash* and return oldest-first."""
        chain: List[LedgerEntry] = []
        current = genome_hash
        seen: set = set()
        while current and current not in seen:
            entry = self._store.get(current)
            if entry is None:
                break
            seen.add(current)
            chain.append(entry)
            current = entry.parent_genome_hash
        chain.reverse()
        return chain

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialize the entire ledger to JSON at *path*."""
        data = {k: v.to_dict() for k, v in self._store.items()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("Ledger saved: %d entries → %s", len(self._store), path)

    def load(self, path: str) -> None:
        """Deserialize a ledger from JSON at *path*, merging into this instance."""
        with open(path, "r") as f:
            data = json.load(f)
        for k, v in data.items():
            self._store[k] = LedgerEntry.from_dict(v)
        logger.debug("Ledger loaded: %d entries ← %s", len(self._store), path)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }
