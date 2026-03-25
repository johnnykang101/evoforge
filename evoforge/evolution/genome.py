"""Architecture Genome.

Encodes agent architecture as an evolvable genotype.
Supports mutation, crossover, constraint propagation, and serialization.

Refined operators (Iteration 2):
- Modular crossover with constraint propagation
- Structural mutation (add/remove modules)
- Topological mutation (rewire inter-module connections)
- Parameter mutation with adaptive step sizes
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import random
import copy
import math


# --- Constraint System ---

# Module compatibility rules: maps (module_type, value) -> set of required constraints
# e.g., a high-throughput memory needs compatible retrieval
COMPATIBILITY_RULES: Dict[Tuple[str, str], Dict[str, List[str]]] = {
    ("memory.strategy", "graph"): {
        "planning.algorithm": ["react", "tree_of_thoughts"],
    },
    ("memory.strategy", "sliding_window"): {
        "memory.compression_strategy": ["prune", "none"],
    },
    ("learning.optimization", "grpo"): {
        "learning.stable": [True],
    },
    ("tools.selection_policy", "learned"): {
        "learning.optimization": ["grpo", "ppo"],
    },
}

# Valid ranges for numeric parameters
PARAMETER_BOUNDS: Dict[str, Tuple[float, float]] = {
    "planning.max_depth": (1, 20),
    "memory.max_size": (100, 100000),
    "tools.timeout_ms": (500, 30000),
    "learning.learning_rate": (0.0001, 0.1),
    "monitoring.evaluation_frequency": (10, 1000),
}

# Optional modules that can be added/removed via structural mutation
OPTIONAL_MODULES: Dict[str, Dict[str, Any]] = {
    "reasoning": {
        "strategy": "chain_of_thought",
        "max_steps": 10,
        "self_consistency": True,
    },
    "meta_learning": {
        "enabled": True,
        "adaptation_rate": 0.01,
        "task_embedding_dim": 64,
    },
    "collaboration": {
        "enabled": True,
        "max_peers": 3,
        "communication_protocol": "message_passing",
    },
}

# Categorical alternatives for all known string parameters
ALTERNATIVES_MAP: Dict[str, List[str]] = {
    "planning.algorithm": ["react", "chain_of_thought", "tree_of_thoughts"],
    "memory.strategy": ["vector_db", "graph", "episodic", "sliding_window"],
    "memory.compression_strategy": ["summarize", "prune", "none"],
    "tools.selection_policy": ["static", "adaptive", "learned"],
    "tools.retry_policy": ["exponential", "linear", "none"],
    "learning.optimization": ["grpo", "ppo", "dpo"],
    "reasoning.strategy": ["chain_of_thought", "tree_of_thoughts", "self_ask"],
    "collaboration.communication_protocol": ["message_passing", "blackboard", "voting"],
}

# Topological connections: which modules feed into which
DEFAULT_TOPOLOGY: Dict[str, List[str]] = {
    "planning": ["memory", "tools"],
    "memory": ["learning"],
    "tools": ["monitoring"],
    "learning": ["planning"],
    "monitoring": [],
}


def _get_nested(config: Dict[str, Any], dotted_path: str) -> Any:
    """Get a value from a nested dict using dotted path."""
    keys = dotted_path.split(".")
    current = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_nested(config: Dict[str, Any], dotted_path: str, value: Any):
    """Set a value in a nested dict using dotted path."""
    keys = dotted_path.split(".")
    current = config
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def propagate_constraints(config: Dict[str, Any]) -> int:
    """Enforce compatibility constraints after crossover or mutation.

    Returns number of corrections made.
    """
    corrections = 0
    for (param_path, trigger_value), required in COMPATIBILITY_RULES.items():
        current = _get_nested(config, param_path)
        if current == trigger_value:
            for constrained_path, allowed_values in required.items():
                actual = _get_nested(config, constrained_path)
                if actual is not None and actual not in allowed_values:
                    _set_nested(config, constrained_path, random.choice(allowed_values))
                    corrections += 1

    # Enforce numeric bounds
    for param_path, (lo, hi) in PARAMETER_BOUNDS.items():
        val = _get_nested(config, param_path)
        if val is not None and isinstance(val, (int, float)):
            clamped = max(lo, min(hi, val))
            if clamped != val:
                if isinstance(val, int):
                    clamped = int(clamped)
                _set_nested(config, param_path, clamped)
                corrections += 1

    return corrections


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
    topology: Dict[str, List[str]] = field(default_factory=dict)
    mutation_log: List[str] = field(default_factory=list)

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize genome with configuration.

        Args:
            config: Configuration dictionary. If None, uses sensible defaults.
        """
        self.config = config or self._default_config()
        self.fitness = None
        self.generation = 0
        self.parent_ids = []
        self.topology = copy.deepcopy(DEFAULT_TOPOLOGY)
        self.mutation_log = []

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

    # --- Parameter Mutation (refined with adaptive step sizes) ---

    def mutate(self, mutation_rate: float = 0.1, strength: float = 0.2) -> 'ArchitectureGenome':
        """Apply random mutations to genome parameters.

        Uses Gaussian noise for continuous params, random swap for categorical,
        and bit-flip for booleans. Respects parameter bounds.

        Args:
            mutation_rate: Probability of mutating each parameter (0.0-1.0)
            strength: Magnitude of mutation for numeric parameters

        Returns:
            New mutated genome (copy)
        """
        child = copy.deepcopy(self)
        child.mutation_log = []

        def mutate_recursive(conf: Dict[str, Any], path: str = ""):
            for key, value in conf.items():
                full_path = f"{path}.{key}" if path else key

                if isinstance(value, dict):
                    mutate_recursive(value, full_path)
                elif isinstance(value, bool):
                    if random.random() < mutation_rate:
                        conf[key] = not value
                        child.mutation_log.append(f"flip:{full_path}")
                elif isinstance(value, (int, float)):
                    if random.random() < mutation_rate:
                        bounds = PARAMETER_BOUNDS.get(full_path)
                        if bounds:
                            lo, hi = bounds
                            # Scale noise to parameter range
                            scale = (hi - lo) * strength
                        else:
                            scale = abs(value) * strength + 0.01
                        noise = random.gauss(0, scale)
                        new_value = value + noise
                        if bounds:
                            new_value = max(lo, min(hi, new_value))
                        if isinstance(value, int):
                            new_value = max(1, int(round(new_value)))
                        elif isinstance(value, float) and 0 <= value <= 1:
                            new_value = max(0.0, min(1.0, new_value))
                        conf[key] = new_value
                        child.mutation_log.append(f"param:{full_path}={new_value:.4g}")
                elif isinstance(value, str):
                    if random.random() < mutation_rate:
                        alternatives = self._get_alternatives(full_path, value)
                        if alternatives:
                            new_val = random.choice(alternatives)
                            conf[key] = new_val
                            child.mutation_log.append(f"cat:{full_path}={new_val}")

        mutate_recursive(child.config)
        propagate_constraints(child.config)
        child.generation = self.generation + 1
        child.parent_ids = [str(id(self))]
        return child

    # --- Structural Mutation ---

    def structural_mutate(self, mutation_rate: float = 0.05) -> 'ArchitectureGenome':
        """Add or remove optional modules from the genome.

        Structural mutations change the architecture's shape by adding
        new capability modules or removing underperforming ones.

        Args:
            mutation_rate: Probability of each structural change

        Returns:
            New structurally mutated genome (copy)
        """
        child = copy.deepcopy(self)
        child.mutation_log = []

        current_modules = set(child.config.keys())
        optional_keys = set(OPTIONAL_MODULES.keys())

        # Try adding a module not yet present
        addable = optional_keys - current_modules
        if addable and random.random() < mutation_rate:
            mod_name = random.choice(list(addable))
            child.config[mod_name] = copy.deepcopy(OPTIONAL_MODULES[mod_name])
            # Wire it into topology
            existing = [k for k in child.topology if k in current_modules]
            if existing:
                feeder = random.choice(existing)
                if mod_name not in child.topology.get(feeder, []):
                    child.topology.setdefault(feeder, []).append(mod_name)
            child.topology.setdefault(mod_name, [])
            child.mutation_log.append(f"add_module:{mod_name}")

        # Try removing an optional module that is present
        removable = optional_keys & current_modules
        if removable and random.random() < mutation_rate:
            mod_name = random.choice(list(removable))
            del child.config[mod_name]
            # Remove from topology
            child.topology.pop(mod_name, None)
            for k in child.topology:
                if mod_name in child.topology[k]:
                    child.topology[k].remove(mod_name)
            child.mutation_log.append(f"remove_module:{mod_name}")

        propagate_constraints(child.config)
        child.generation = self.generation + 1
        child.parent_ids = [str(id(self))]
        return child

    # --- Topological Mutation ---

    def topological_mutate(self, mutation_rate: float = 0.03) -> 'ArchitectureGenome':
        """Rewire inter-module connections in the topology graph.

        Changes which modules feed data into which, enabling discovery
        of novel information flow patterns.

        Args:
            mutation_rate: Probability of rewiring each connection

        Returns:
            New topologically mutated genome (copy)
        """
        child = copy.deepcopy(self)
        child.mutation_log = []
        modules = list(child.config.keys())

        if len(modules) < 2:
            return child

        for source in list(child.topology.keys()):
            if source not in modules:
                continue
            if random.random() < mutation_rate:
                # Rewire: pick a new random target
                possible_targets = [m for m in modules if m != source]
                if possible_targets:
                    new_target = random.choice(possible_targets)
                    if child.topology[source]:
                        # Replace one existing connection
                        idx = random.randrange(len(child.topology[source]))
                        old_target = child.topology[source][idx]
                        child.topology[source][idx] = new_target
                        child.mutation_log.append(
                            f"rewire:{source}->{old_target} to {source}->{new_target}"
                        )
                    else:
                        # Add a new connection
                        child.topology[source].append(new_target)
                        child.mutation_log.append(f"connect:{source}->{new_target}")

        child.generation = self.generation + 1
        child.parent_ids = [str(id(self))]
        return child

    # --- Modular Crossover with Constraint Propagation ---

    def crossover(self, other: 'ArchitectureGenome', crossover_rate: float = 0.5) -> 'ArchitectureGenome':
        """Modular crossover: swap entire modules between parents, then enforce constraints.

        Unlike parameter-level crossover, this operates at the module level
        (planning, memory, tools, etc.) to preserve intra-module coherence.
        After swapping, constraint propagation ensures compatibility.

        Args:
            other: Second parent genome
            crossover_rate: Probability of taking each module from other parent

        Returns:
            New child genome with constraints enforced
        """
        child = ArchitectureGenome()

        # Module-level crossover
        all_modules = set(self.config.keys()) | set(other.config.keys())
        child_config = {}

        for module in all_modules:
            in_self = module in self.config
            in_other = module in other.config

            if in_self and in_other:
                # Both parents have this module — pick one
                if random.random() < crossover_rate:
                    child_config[module] = copy.deepcopy(other.config[module])
                else:
                    child_config[module] = copy.deepcopy(self.config[module])
            elif in_self:
                # Only in first parent — inherit with probability
                if random.random() < 0.7:
                    child_config[module] = copy.deepcopy(self.config[module])
            else:
                # Only in second parent — inherit with probability
                if random.random() < 0.3:
                    child_config[module] = copy.deepcopy(other.config[module])

        child.config = child_config

        # Merge topologies
        child.topology = copy.deepcopy(self.topology)
        for src, targets in other.topology.items():
            if src in child.config:
                existing = set(child.topology.get(src, []))
                for t in targets:
                    if t in child.config and t not in existing:
                        child.topology.setdefault(src, []).append(t)

        # Remove topology entries for modules not in child
        child.topology = {
            k: [t for t in v if t in child.config]
            for k, v in child.topology.items()
            if k in child.config
        }

        # Enforce constraints
        propagate_constraints(child.config)

        child.generation = max(self.generation, other.generation) + 1
        child.parent_ids = [str(id(self)), str(id(other))]
        return child

    def _get_alternatives(self, parameter_path: str, current_value: str) -> List[str]:
        """Get alternative values for a categorical parameter."""
        alts = ALTERNATIVES_MAP.get(parameter_path, [])
        return [a for a in alts if a != current_value]

    def distance(self, other: 'ArchitectureGenome') -> float:
        """Compute normalized distance between two genomes for diversity measurement.

        Returns a value in [0, 1] where 0 means identical and 1 means maximally different.
        """
        diffs = 0
        total = 0

        def compare_recursive(c1: Dict[str, Any], c2: Dict[str, Any]):
            nonlocal diffs, total
            all_keys = set(c1.keys()) | set(c2.keys())
            for key in all_keys:
                total += 1
                if key not in c1 or key not in c2:
                    diffs += 1
                elif isinstance(c1[key], dict) and isinstance(c2[key], dict):
                    compare_recursive(c1[key], c2[key])
                elif c1[key] != c2[key]:
                    if isinstance(c1[key], (int, float)) and isinstance(c2[key], (int, float)):
                        bounds = PARAMETER_BOUNDS.get(key)
                        if bounds:
                            span = bounds[1] - bounds[0]
                            diffs += min(1.0, abs(c1[key] - c2[key]) / span)
                        else:
                            diffs += min(1.0, abs(c1[key] - c2[key]) / (abs(c1[key]) + 1e-8))
                    else:
                        diffs += 1

        compare_recursive(self.config, other.config)
        return diffs / max(total, 1)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize genome to dictionary."""
        return {
            "config": self.config,
            "fitness": self.fitness,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "topology": self.topology,
            "mutation_log": self.mutation_log,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchitectureGenome':
        """Deserialize genome from dictionary."""
        genome = cls(config=data.get("config"))
        genome.fitness = data.get("fitness")
        genome.generation = data.get("generation", 0)
        genome.parent_ids = data.get("parent_ids", [])
        genome.topology = data.get("topology", copy.deepcopy(DEFAULT_TOPOLOGY))
        genome.mutation_log = data.get("mutation_log", [])
        return genome

    def __str__(self) -> str:
        modules = list(self.config.keys())
        return (f"ArchitectureGenome(generation={self.generation}, "
                f"fitness={self.fitness}, modules={modules})")


class GenomeParser:
    """Utility for parsing and validating genome configurations."""

    @staticmethod
    def validate(config: Dict[str, Any]) -> List[str]:
        """Validate a genome configuration, returning list of issues."""
        issues = []
        required_modules = {"planning", "memory", "tools", "learning", "monitoring"}
        present = set(config.keys())
        missing = required_modules - present
        if missing:
            issues.append(f"Missing required modules: {missing}")

        for param_path, (lo, hi) in PARAMETER_BOUNDS.items():
            val = _get_nested(config, param_path)
            if val is not None and isinstance(val, (int, float)):
                if val < lo or val > hi:
                    issues.append(f"{param_path}={val} out of bounds [{lo}, {hi}]")

        return issues
