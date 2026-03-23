"""
EvoForge Core - Genome representation and base types.
Defines the genetic encoding for self-evolving agent architectures.
"""

from typing import Dict, List, Any, Optional, TypedDict
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json


class ModuleType(Enum):
    """Types of modules that can be assembled into an agent."""
    PLANNER = "planner"
    MEMORY = "memory"
    SELECTOR = "selector"
    EXECUTOR = "executor"
    EVALUATOR = "evaluator"
    REFLECTOR = "reflector"
    TOOL = "tool"


class ConnectionType(Enum):
    """Types of connections between modules."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FEEDBACK = "feedback"


@dataclass
class ModuleGenome:
    """
    Genetic representation of a single module in the agent architecture.
    """
    id: str
    type: ModuleType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0
    performance_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "config": self.config,
            "parameters": self.parameters,
            "fitness": self.fitness,
            "performance_history": self.performance_history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModuleGenome':
        return cls(
            id=data["id"],
            type=ModuleType(data["type"]),
            name=data["name"],
            config=data.get("config", {}),
            parameters=data.get("parameters", {}),
            fitness=data.get("fitness", 0.0),
            performance_history=data.get("performance_history", [])
        )

    def mutate_parameters(self, mutation_rate: float = 0.1, intensity: float = 0.2):
        """
        Apply Gaussian noise to numeric parameters.
        """
        import random
        for key, value in self.parameters.items():
            if isinstance(value, (int, float)):
                if random.random() < mutation_rate:
                    if isinstance(value, int):
                        delta = int(random.gauss(0, intensity * abs(value) if value != 0 else intensity))
                        self.parameters[key] = max(0, value + delta)
                    else:
                        delta = random.gauss(0, intensity * abs(value) if value != 0 else intensity)
                        self.parameters[key] = value + delta

    def mutate_structure(self) -> Optional['ModuleGenome']:
        """
        Potentially alter module configuration. Returns a new mutated module or None.
        """
        import random
        mutation_type = random.choice(['config_adjust', 'parameter_swap', None])
        if mutation_type is None:
            return None

        new_module = ModuleGenome.from_dict(self.to_dict())

        if mutation_type == 'config_adjust':
            # Add, remove, or modify config keys
            action = random.choice(['add', 'remove', 'modify'])
            if action == 'add' and len(new_module.config) < 10:
                new_key = f"config_{random.randint(1000, 9999)}"
                new_module.config[new_key] = random.choice([True, False, 0.5, "auto"])
            elif action == 'remove' and new_module.config:
                key_to_remove = random.choice(list(new_module.config.keys()))
                del new_module.config[key_to_remove]
            elif action == 'modify' and new_module.config:
                key = random.choice(list(new_module.config.keys()))
                if isinstance(new_module.config[key], bool):
                    new_module.config[key] = not new_module.config[key]
                elif isinstance(new_module.config[key], (int, float)):
                    new_module.config[key] *= random.uniform(0.5, 2.0)

        return new_module


@dataclass
class ConnectionGenome:
    """
    Genetic representation of a connection between two modules.
    """
    id: str
    source_module_id: str
    target_module_id: str
    connection_type: ConnectionType
    condition: Optional[Dict[str, Any]] = None  # For CONDITIONAL connections

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_module_id": self.source_module_id,
            "target_module_id": self.target_module_id,
            "connection_type": self.connection_type.value,
            "condition": self.condition
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionGenome':
        return cls(
            id=data["id"],
            source_module_id=data["source_module_id"],
            target_module_id=data["target_module_id"],
            connection_type=ConnectionType(data["connection_type"]),
            condition=data.get("condition")
        )


@dataclass
class AgentGenome:
    """
    Complete genetic representation of an agent architecture.
    This is the primary chromosome that undergoes evolution.
    """
    id: str
    name: str
    modules: List[ModuleGenome] = field(default_factory=list)
    connections: List[ConnectionGenome] = field(default_factory=list)
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)  # Supports multiple parents for crossover
    creation_timestamp: float = field(default_factory=lambda: __import__('time').time())

    # Architectural constraints
    @property
    def is_valid(self) -> bool:
        """Check if the architecture satisfies basic constraints."""
        if not self.modules:
            return False
        if not self.connections:
            return False
        # All connected modules must exist
        module_ids = {m.id for m in self.modules}
        for conn in self.connections:
            if conn.source_module_id not in module_ids:
                return False
            if conn.target_module_id not in module_ids:
                return False
        # Must have at least one entry point (module with no incoming connections)
        incoming = {c.target_module_id for c in self.connections}
        entry_points = module_ids - incoming
        return len(entry_points) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "modules": [m.to_dict() for m in self.modules],
            "connections": [c.to_dict() for c in self.connections],
            "fitness": self.fitness,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "creation_timestamp": self.creation_timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentGenome':
        modules = [ModuleGenome.from_dict(m) for m in data.get("modules", [])]
        connections = [ConnectionGenome.from_dict(c) for c in data.get("connections", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            modules=modules,
            connections=connections,
            fitness=data.get("fitness", 0.0),
            generation=data.get("generation", 0),
            parent_ids=data.get("parent_ids", [])
        )

    def get_module_by_id(self, module_id: str) -> Optional[ModuleGenome]:
        for module in self.modules:
            if module.id == module_id:
                return module
        return None

    def get_modules_by_type(self, module_type: ModuleType) -> List[ModuleGenome]:
        return [m for m in self.modules if m.type == module_type]

    def add_module(self, module: ModuleGenome):
        self.modules.append(module)

    def add_connection(self, connection: ConnectionGenome):
        self.connections.append(connection)

    def copy(self) -> 'AgentGenome':
        """Create a deep copy of the genome."""
        import copy
        return AgentGenome.from_dict(copy.deepcopy(self.to_dict()))

    def crossover(self, other: 'AgentGenome') -> 'AgentGenome':
        """
        Perform crossover with another genome.
        Mixes modules and connections from both parents.
        """
        import random
        child = AgentGenome(
            id=str(uuid.uuid4()),
            name=f"Crossover_{self.name}x{other.name}",
            modules=[],
            connections=[],
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[self.id, other.id]
        )

        # Crossover modules: take random subset from each parent
        self_modules = random.sample(self.modules, k=len(self.modules) // 2)
        other_modules = random.sample(other.modules, k=len(other.modules) // 2)

        # Re-map IDs to avoid collisions
        id_map = {}
        for module in self_modules + other_modules:
            old_id = module.id
            new_id = str(uuid.uuid4())
            id_map[old_id] = new_id
            new_module = ModuleGenome.from_dict(module.to_dict())
            new_module.id = new_id
            child.add_module(new_module)

        # Crossover connections: take connections that map to kept modules
        for conn in self.connections + other.connections:
            if conn.source_module_id in id_map and conn.target_module_id in id_map:
                new_conn = ConnectionGenome.from_dict(conn.to_dict())
                new_conn.source_module_id = id_map[conn.source_module_id]
                new_conn.target_module_id = id_map[conn.target_module_id]
                new_conn.id = str(uuid.uuid4())
                child.add_connection(new_conn)

        # If child is invalid, return a copy of fitter parent
        if not child.is_valid:
            return self.copy() if self.fitness >= other.fitness else other.copy()

        return child

    def mutate_connections(self, mutation_rate: float = 0.1) -> None:
        """
        Apply topological mutations to connections.
        - Add new random connection
        - Remove existing connection
        - Rewire connection
        """
        import random
        if len(self.modules) < 2:
            return

        module_ids = [m.id for m in self.modules]
        existing_connections = {(c.source_module_id, c.target_module_id) for c in self.connections}

        if random.random() < mutation_rate:
            mutation_type = random.choice(['add', 'remove', 'rewire'])
            if mutation_type == 'add':
                # Add a new connection that doesn't already exist
                source = random.choice(module_ids)
                target = random.choice(module_ids)
                if source != target and (source, target) not in existing_connections:
                    conn_id = str(uuid.uuid4())
                    conn_type = random.choice(list(ConnectionType))
                    conn = ConnectionGenome(
                        id=conn_id,
                        source_module_id=source,
                        target_module_id=target,
                        connection_type=conn_type
                    )
                    self.add_connection(conn)

            elif mutation_type == 'remove' and self.connections:
                # Remove a random connection
                idx = random.randrange(len(self.connections))
                self.connections.pop(idx)

            elif mutation_type == 'rewire' and self.connections:
                # Rewire a random connection's source or target
                conn = random.choice(self.connections)
                if random.random() < 0.5:
                    conn.source_module_id = random.choice(module_ids)
                else:
                    conn.target_module_id = random.choice(module_ids)

    def mutate(self, mutation_rate: float = 0.1, intensity: float = 0.2) -> 'AgentGenome':
        """
        Full mutation operator combining parameter and structural mutations.
        Returns a new mutated genome (or self if no mutation occurred).
        """
        import random
        mutated = self.copy()

        # Mutate module parameters
        for module in mutated.modules:
            module.mutate_parameters(mutation_rate, intensity)

        # Potentially mutate individual modules structurally
        for module in mutated.modules:
            if random.random() < mutation_rate * 0.5:
                new_module = module.mutate_structure()
                if new_module:
                    # Replace the module
                    for i, m in enumerate(mutated.modules):
                        if m.id == module.id:
                            mutated.modules[i] = new_module
                            break

        # Mutate connection topology
        mutated.mutate_connections(mutation_rate)

        # If no changes occurred, retry once
        if mutated.to_dict() == self.to_dict():
            return self.mutate(mutation_rate, intensity)

        return mutated


    def mutate_connections(self, mutation_rate: float = 0.1) -> None:
        """
        Apply topological mutations to connections.
        - Add new random connection
        - Remove existing connection
        - Rewire connection
        """
        import random
        if len(self.modules) < 2:
            return

        module_ids = [m.id for m in self.modules]
        existing_connections = {(c.source_module_id, c.target_module_id) for c in self.connections}

        if random.random() < mutation_rate:
            mutation_type = random.choice(['add', 'remove', 'rewire'])
            if mutation_type == 'add':
                # Add a new connection that doesn't already exist
                source = random.choice(module_ids)
                target = random.choice(module_ids)
                if source != target and (source, target) not in existing_connections:
                    conn_id = str(uuid.uuid4())
                    conn_type = random.choice(list(ConnectionType))
                    conn = ConnectionGenome(
                        id=conn_id,
                        source_module_id=source,
                        target_module_id=target,
                        connection_type=conn_type
                    )
                    self.add_connection(conn)

            elif mutation_type == 'remove' and self.connections:
                # Remove a random connection
                idx = random.randrange(len(self.connections))
                self.connections.pop(idx)

            elif mutation_type == 'rewire' and self.connections:
                # Rewire a random connection's source or target
                conn = random.choice(self.connections)
                if random.random() < 0.5:
                    conn.source_module_id = random.choice(module_ids)
                else:
                    conn.target_module_id = random.choice(module_ids)

    def mutate(self, mutation_rate: float = 0.1, intensity: float = 0.2) -> 'AgentGenome':
        """
        Full mutation operator combining parameter and structural mutations.
        Returns a new mutated genome (or self if no mutation occurred).
        """
        import random
        mutated = self.copy()

        # Mutate module parameters
        for module in mutated.modules:
            module.mutate_parameters(mutation_rate, intensity)

        # Potentially mutate individual modules structurally
        for module in mutated.modules:
            if random.random() < mutation_rate * 0.5:
                new_module = module.mutate_structure()
                if new_module:
                    # Replace the module
                    for i, m in enumerate(mutated.modules):
                        if m.id == module.id:
                            mutated.modules[i] = new_module
                            break

        # Mutate connection topology
        mutated.mutate_connections(mutation_rate)

        # If no changes occurred, retry once
        if mutated.to_dict() == self.to_dict():
            return self.mutate(mutation_rate, intensity)

        return mutated

