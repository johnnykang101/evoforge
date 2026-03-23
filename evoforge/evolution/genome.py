"""Architecture Genome.

Encodes agent architecture as an evolvable genotype.
Supports mutation, crossover, and serialization.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import random
import copy

@dataclass
class ArchitectureGenome:
    """Represents an agent's architecture as evolvable parameters.

    Genome configuration schema:
    {
      "planning": {
        "algorithm": "react",  # react | chain_of_thought | tree_of_thoughts
        "max_depth": 5,
        "backtrack": true
      },
      "memory": {
        "strategy": "vector_db",  # vector_db | graph | episodic | sliding_window
        "max_size": 10000,
        "compression_strategy": "summarize"  # summarize | prune | none
      },
      "tools": {
        "selection_policy": "adaptive",  # static | adaptive | learned
        "timeout_ms": 5000,
        "retry_policy": "exponential"
      },
      "learning": {
        "learning_rate": 0.001,
        "optimization": "grpo",  # grpo | ppo | dpo
        "stable": true
      },
      "monitoring": {
        "telemetry_enabled": true,
        "evaluation_frequency": 100,
        "self_critique": true
      }
    }
    """
    config: Dict[str, Any] = field(default_factory=dict)
    fitness: Optional[float] = None
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize genome with configuration.

        Args:
            config: Configuration dictionary. If None, uses sensible defaults.
        """
        self.config = config or self._default_config()
        self.fitness = None
        self.generation = 0
        self.parent_ids = []

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "planning": {
                "algorithm": "react",
                "max_depth": 5,
                "backtrack": True
            },
            "memory": {
                "strategy": "vector_db",
                "max_size": 10000,
                "compression_strategy": "summarize"
            },
            "tools": {
                "selection_policy": "adaptive",
                "timeout_ms": 5000,
                "retry_policy": "exponential"
            },
            "learning": {
                "learning_rate": 0.001,
                "optimization": "grpo",
                "stable": True
            },
            "monitoring": {
                "telemetry_enabled": True,
                "evaluation_frequency": 100,
                "self_critique": True
            }
        }

    def mutate(self, mutation_rate: float = 0.1, strength: float = 0.2) -> 'ArchitectureGenome':
        """Apply random mutations to genome parameters.

        Args:
            mutation_rate: Probability of mutating each parameter (0.0-1.0)
            strength: Magnitude of mutation for numeric parameters

        Returns:
            New mutated genome (copy)
        """
        child = copy.deepcopy(self)

        def mutate_recursive(conf: Dict[str, Any], path: str = ""):
            for key, value in conf.items():
                full_path = f"{path}.{key}" if path else key

                if isinstance(value, dict):
                    mutate_recursive(value, full_path)
                elif isinstance(value, bool):
                    if random.random() < mutation_rate:
                        conf[key] = not value
                elif isinstance(value, (int, float)):
                    if random.random() < mutation_rate:
                        # Apply Gaussian noise
                        noise = random.gauss(0, value * strength + 0.01)
                        new_value = value + noise
                        # Keep in bounds
                        if isinstance(value, int):
                            new_value = max(1, int(new_value))
                        elif isinstance(value, float) and 0 <= value <= 1:
                            new_value = max(0.0, min(1.0, new_value))
                        conf[key] = new_value
                elif isinstance(value, str):
                    # String values are categorical - pick random alternative
                    if random.random() < mutation_rate:
                        alternatives = self._get_alternatives(full_path, value)
                        if alternatives:
                            conf[key] = random.choice(alternatives)

        mutate_recursive(child.config)
        child.generation = self.generation + 1
        child.parent_ids = [str(id(self))]  # Reference to parent
        return child

    def _get_alternatives(self, parameter_path: str, current_value: str) -> List[str]:
        """Get alternative values for a categorical parameter."""
        alternatives_map = {
            "planning.algorithm": ["react", "chain_of_thought", "tree_of_thoughts"],
            "memory.strategy": ["vector_db", "graph", "episodic", "sliding_window"],
            "memory.compression_strategy": ["summarize", "prune", "none"],
            "tools.selection_policy": ["static", "adaptive", "learned"],
            "tools.retry_policy": ["exponential", "linear", "none"],
            "learning.optimization": ["grpo", "ppo", "dpo"]
        }
        alts = alternatives_map.get(parameter_path, [])
        return [a for a in alts if a != current_value]

    def crossover(self, other: 'ArchitectureGenome', crossover_rate: float = 0.5) -> 'ArchitectureGenome':
        """Create child genome by mixing configurations with another genome.

        Args:
            other: Second parent genome
            crossover_rate: Probability of taking from other at each decision point

        Returns:
            New child genome
        """
        child = ArchitectureGenome()

        def crossover_recursive(conf1: Dict[str, Any], conf2: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for key in conf1:
                if key in conf2:
                    val1, val2 = conf1[key], conf2[key]
                    if isinstance(val1, dict) and isinstance(val2, dict):
                        result[key] = crossover_recursive(val1, val2)
                    elif random.random() < crossover_rate:
                        result[key] = val2
                    else:
                        result[key] = val1
                else:
                    result[key] = conf1[key]
            return result

        child.config = crossover_recursive(self.config, other.config)
        child.generation = max(self.generation, other.generation) + 1
        child.parent_ids = [str(id(self)), str(id(other))]
        return child

    def to_dict(self) -> Dict[str, Any]:
        """Serialize genome to dictionary."""
        return {
            "config": self.config,
            "fitness": self.fitness,
            "generation": self.generation,
            "parent_ids": self.parent_ids
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchitectureGenome':
        """Deserialize genome from dictionary."""
        genome = cls(config=data.get("config"))
        genome.fitness = data.get("fitness")
        genome.generation = data.get("generation", 0)
        genome.parent_ids = data.get("parent_ids", [])
        return genome

    def __str__(self) -> str:
        return f"ArchitectureGenome(generation={self.generation}, fitness={self.fitness})"
