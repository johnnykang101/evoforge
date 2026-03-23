"""Skill Crystallization Cache.

Central repository for skills with lifecycle management and validation pipeline.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from evoforge.skills.states import SkillState, SkillRecord
from evoforge.skills.validation import ValidationPipeline, ValidationStage

class SkillCrystallizationCache:
    """Manages skill lifecycle from prototype to crystallized production.

    The Skill Cache is the central repository for all skills in the system.
    It enforces lifecycle rules, runs validation pipelines, and ensures
    crystallized skills remain immutable and versioned.

    Key responsibilities:
    - Store and retrieve skills by ID
    - Track execution metrics (counts, latency, success rate)
    - Enforce state transitions (prototype → candidate → crystallized)
    - Run validation pipelines before promotion
    - Prevent modifications to crystallized skills
    - Maintain version history and deprecation trails
    """

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize skill cache.

        Args:
            storage_path: Optional path for persistent storage.
                         If None, uses in-memory storage.
        """
        self.storage_path = storage_path
        self.skills: Dict[str, SkillRecord] = {}
        self.validation_pipeline = ValidationPipeline()
        self._load_from_disk() if storage_path else None

    def register(self, skill: Any, name: str, description: str) -> str:
        """Register a new skill as a PROTOTYPE.

        Args:
            skill: The skill object (must have execute method)
            name: Human-readable name
            description: Description of functionality

        Returns:
            skill_id for future reference
        """
        import uuid
        skill_id = str(uuid.uuid4())[:8]

        record = SkillRecord(
            skill_id=skill_id,
            name=name,
            description=description,
            state=SkillState.PROTOTYPE,
            execution_count=0,
            success_count=0,
            failure_count=0
        )

        # Store skill object separately (not serialized in record)
        # In production, use persistent object storage
        self.skills[skill_id] = record
        self._persist_metadata(record)

        return skill_id

    def execute(self, skill_id: str, *args, **kwargs) -> Any:
        """Execute a skill and update its metrics.

        Args:
            skill_id: ID of the skill to execute
            *args, **kwargs: Arguments passed to skill.execute()

        Returns:
            Result from skill execution

        Raises:
            ValueError: If skill_id not found or skill is locked
        """
        if skill_id not in self.skills:
            raise ValueError(f"Skill {skill_id} not registered")

        record = self.skills[skill_id]

        if record.locked and record.state == SkillState.CRYSTALLIZED:
            raise ValueError(f"Skill {skill_id} is crystallized and locked from modification")

        # Record execution start
        start = datetime.utcnow()
        try:
            # In production, retrieve actual skill object from storage
            result = self._get_skill_object(skill_id).execute(*args, **kwargs)
            success = True
            record.success_count += 1
        except Exception as e:
            success = False
            record.failure_count += 1
            raise e
        finally:
            record.execution_count += 1
            record.last_executed = datetime.utcnow()
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            # Update rolling average latency
            record.average_latency_ms = (
                (record.average_latency_ms * (record.execution_count - 1) + duration)
                / record.execution_count
            )

            # Check for automatic state transitions
            self._check_auto_transition(record)

            self._persist_metadata(record)

        return result

    def _get_skill_object(self, skill_id: str) -> Any:
        """Retrieve the actual skill object (placeholder)."""
        # In production, this would load from persistent storage
        # For now, this is a stub - skills would be stored separately
        raise NotImplementedError("Skill object storage not implemented")

    def _check_auto_transition(self, record: SkillRecord):
        """Check if skill can auto-transition based on execution count."""
        if record.execution_count >= 50 and record.state == SkillState.CANDIDATE:
            # Auto-promote to Crystallized if validation passed
            # In production, check validation history
            record.state = SkillState.CRYSTALLIZED
            record.locked = True
        elif record.execution_count >= 5 and record.state == SkillState.PROTOTYPE:
            record.state = SkillState.CANDIDATE

    def promote(self, skill_id: str, target_state: SkillState) -> bool:
        """Manually promote a skill after validation.

        Returns:
            True if promotion succeeded, False if requirements not met
        """
        if skill_id not in self.skills:
            return False

        record = self.skills[skill_id]

        if not record.can_transition_to(target_state):
            return False

        # Run validation for the target stage
        required_stage = self._state_to_validation_stage(target_state)
        if required_stage:
            result = self.validation_pipeline.validate(None, required_stage)
            if not result.passed:
                return False
            record.validation_history.append({
                "stage": required_stage.name,
                "passed": True,
                "timestamp": datetime.utcnow().isoformat()
            })

        record.state = target_state
        if target_state == SkillState.CRYSTALLIZED:
            record.locked = True

        self._persist_metadata(record)
        return True

    def _state_to_validation_stage(self, state: SkillState) -> Optional[ValidationStage]:
        """Map skill state to required validation stage."""
        mapping = {
            SkillState.CANDIDATE: ValidationStage.UNIT_TESTS,
            SkillState.CRYSTALLIZED: ValidationStage.REGRESSION,
        }
        return mapping.get(state)

    def deprecate(self, skill_id: str) -> bool:
        """Archive a skill, triggering deprecation warnings for dependents."""
        if skill_id not in self.skills:
            return False

        record = self.skills[skill_id]
        record.state = SkillState.ARCHIVED
        self._persist_metadata(record)
        return True

    def get_skill_record(self, skill_id: str) -> Optional[SkillRecord]:
        """Retrieve metadata for a skill."""
        return self.skills.get(skill_id)

    def list_skills(self, state: Optional[SkillState] = None) -> List[SkillRecord]:
        """List all skills, optionally filtered by state."""
        skills = list(self.skills.values())
        if state:
            return [s for s in skills if s.state == state]
        return skills

    def _persist_metadata(self, record: SkillRecord):
        """Persist skill metadata to disk (if storage_path configured)."""
        if self.storage_path:
            import json
            import os
            os.makedirs(self.storage_path, exist_ok=True)
            path = f"{self.storage_path}/{record.skill_id}.json"
            with open(path, 'w') as f:
                json.dump(record.to_dict(), f, indent=2)

    def _load_from_disk(self):
        """Load skill metadata from disk."""
        if not self.storage_path:
            return
        import json
        import os
        if not os.path.exists(self.storage_path):
            return
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                path = f"{self.storage_path}/{filename}"
                with open(path, 'r') as f:
                    data = json.load(f)
                    record = SkillRecord(
                        skill_id=data['skill_id'],
                        name=data['name'],
                        description=data['description'],
                        state=SkillState[data['state']],
                        execution_count=data['execution_count'],
                        created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
                        last_executed=datetime.fromisoformat(data['last_executed']) if data.get('last_executed') else None,
                        success_count=data['success_count'],
                        failure_count=data['failure_count'],
                        average_latency_ms=data['average_latency_ms'],
                        version=data['version'],
                        locked=data.get('locked', False)
                    )
                    self.skills[record.skill_id] = record
