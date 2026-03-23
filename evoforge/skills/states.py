"""Skill Lifecycle States.

Defines the state machine for skill progression: Prototype → Candidate →
Crystallized → Archived. Each state has specific validation requirements.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime

class SkillState(Enum):
    """Lifecycle states for skills."""
    PROTOTYPE = auto()      # 0-5 executions: casual logs only
    CANDIDATE = auto()     # 5-50 executions: basic telemetry, requires testing
    CRYSTALLIZED = auto()  # 50+ executions: immutable, versioned, production-certified
    ARCHIVED = auto()      # Retired: read-only, triggers deprecation warnings

@dataclass
class SkillRecord:
    """Complete record of a skill's lifecycle."""
    skill_id: str
    name: str
    description: str
    state: SkillState
    execution_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    average_latency_ms: float = 0.0
    version: int = 1
    locked: bool = False  # Crystallized skills cannot be modified
    validation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def can_transition_to(self, new_state: SkillState) -> bool:
        """Check if state transition is allowed."""
        allowed = {
            SkillState.PROTOTYPE: [SkillState.CANDIDATE],
            SkillState.CANDIDATE: [SkillState.CRYSTALLIZED, SkillState.PROTOTYPE],
            SkillState.CRYSTALLIZED: [SkillState.ARCHIVED],
            SkillState.ARCHIVED: []  # Terminal state
        }
        return new_state in allowed.get(self.state, [])

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "state": self.state.name,
            "execution_count": self.execution_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "success_rate": self.success_rate,
            "version": self.version,
            "locked": self.locked
        }
