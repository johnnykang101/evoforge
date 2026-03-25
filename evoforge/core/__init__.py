"""Convergent Knowledge Synthesis Engine (CKSE).

Cross-architecture learning system that extracts causal insights from agent
trajectories and uses them to guide architectural evolution.
"""

from .world_model import WorldModel as WorldModelAbstractor
from .causal_reader import CausalReader
from .synthesizer import KnowledgeSynthesizer
from .token_cache import TokenCache
from .context_compression import ContextCompressor
from .fitness_ledger import FitnessLedger, LedgerEntry, compute_genome_hash
from .validation_battery import ValidationBattery, ValidationTask, BatteryResult

__all__ = [
    "WorldModelAbstractor",
    "CausalReader",
    "KnowledgeSynthesizer",
    "TokenCache",
    "ContextCompressor",
    "FitnessLedger",
    "LedgerEntry",
    "compute_genome_hash",
    "ValidationBattery",
    "ValidationTask",
    "BatteryResult",
]
