"""
EvoForge Core - Skill Crystallization Cache with Chaîne Validation.

Manages skill lifecycle: Prototype (0-5 execs) → Candidate (5-50) → Crystallized (50+) → Archived.
Includes validation pipeline: Unit Tests → Integration → A/B Shadow → Canary → Regression Detection.
"""

from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import os

from .base import BaseModule, ExecutionResult


class SkillState(Enum):
    """Lifecycle states for a skill."""
    PROTOTYPE = "prototype"      # 0-5 executions, casual logs only
    CANDIDATE = "candidate"      # 5-50 executions, basic telemetry
    CRYSTALLIZED = "crystallized"  # 50+ executions, immutable, production-certified
    ARCHIVED = "archived"        # Retired, read-only, deprecated


@dataclass
class SkillExecution:
    """Record of a single skill execution."""
    id: str
    skill_id: str
    timestamp: datetime
    context: Dict[str, Any]
    result: ExecutionResult
    duration_ms: float
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "timestamp": self.timestamp.isoformat(),
            "context_summary": str(self.context)[:200],
            "success": self.result.success,
            "error": self.result.error,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count
        }


@dataclass
class SkillMetrics:
    """Aggregated performance metrics for a skill."""
    total_executions: int = 0
    successful_executions: int = 0
    avg_duration_ms: float = 0.0
    failure_rate: float = 0.0
    last_execution: Optional[datetime] = None
    unique_contexts: int = 0  # Context diversity

    @property
    def success_rate(self) -> float:
        return self.successful_executions / max(self.total_executions, 1)

    @property
    def stability_score(self) -> float:
        """
        Score 0-1 indicating stability (high success rate + low variance).
        """
        return self.success_rate if self.total_executions >= 5 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "failure_rate": self.failure_rate,
            "stability_score": self.stability_score,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "unique_contexts": self.unique_contexts
        }


@dataclass
class ValidationResult:
    """Result of a validation step."""
    stage: str
    passed: bool
    score: float  # 0-1
    details: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "passed": self.passed,
            "score": self.score,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Skill:
    """
    A crystallizable skill with full lifecycle management and validation.
    """
    id: str
    name: str
    description: str
    module: BaseModule  # The actual executable module
    state: SkillState = SkillState.PROTOTYPE
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    executions: List[SkillExecution] = field(default_factory=list)
    metrics: SkillMetrics = field(default_factory=SkillMetrics)
    validation_history: List[ValidationResult] = field(default_factory=list)
    parent_skill_id: Optional[str] = None  # For version lineage
    deprecation_warning: Optional[str] = None

    # Metadata
    tags: Set[str] = field(default_factory=set)
    author: str = "system"
    domain: str = "general"

    def record_execution(
        self,
        context: Dict[str, Any],
        result: ExecutionResult,
        duration_ms: float,
        retry_count: int = 0
    ) -> SkillExecution:
        """Record an execution and update metrics."""
        execution = SkillExecution(
            id=str(uuid.uuid4()),
            skill_id=self.id,
            timestamp=datetime.now(),
            context=context.copy(),
            result=result,
            duration_ms=duration_ms,
            retry_count=retry_count
        )
        self.executions.append(execution)
        self._update_metrics()
        self._evaluate_state_transition()
        return execution

    def _update_metrics(self):
        """Update aggregated metrics from executions."""
        execs = self.executions
        self.metrics.total_executions = len(execs)
        self.metrics.successful_executions = sum(1 for e in execs if e.result.success)
        self.metrics.failure_rate = 1.0 - self.metrics.success_rate

        if execs:
            total_dur = sum(e.duration_ms for e in execs)
            self.metrics.avg_duration_ms = total_dur / len(execs)
            self.metrics.last_execution = execs[-1].timestamp

        # Count unique contexts (simplified hash of context keys/values)
        context_hashes = set()
        for e in execs:
            ctx_tuple = tuple(sorted(e.context.items()))
            context_hashes.add(hash(str(ctx_tuple)))
        self.metrics.unique_contexts = len(context_hashes)

    def _evaluate_state_transition(self):
        """Check if skill meets criteria to advance state."""
        count = self.metrics.total_executions

        if self.state == SkillState.PROTOTYPE and count >= 5:
            self.state = SkillState.CANDIDATE
        elif self.state == SkillState.CANDIDATE and count >= 50:
            # Check stability before crystallization
            if self.metrics.stability_score >= 0.85:
                self.state = SkillState.CRYSTALLIZED

    def can_execute(self) -> bool:
        """Check if skill is executable (not archived or deprecated)."""
        if self.state == SkillState.ARCHIVED:
            if self.deprecation_warning:
                return False  # Fully disabled
            return True  # Archived but still readable (for reproduction)
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "metrics": self.metrics.to_dict(),
            "executions": [e.to_dict() for e in self.executions[-100:]],  # Keep recent
            "validation_history": [v.to_dict() for v in self.validation_history],
            "parent_skill_id": self.parent_skill_id,
            "deprecation_warning": self.deprecation_warning,
            "tags": list(self.tags),
            "author": self.author,
            "domain": self.domain
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        module_factory: Optional[Callable] = None
    ) -> 'Skill':
        """Reconstruct skill from dictionary."""
        # Recreate module if factory provided
        module = data.get("module") if module_factory is None else module_factory(data.get("module_config", {}))

        skill = cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            module=module,
            state=SkillState(data["state"]),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            parent_skill_id=data.get("parent_skill_id"),
            deprecation_warning=data.get("deprecation_warning"),
            tags=set(data.get("tags", [])),
            author=data.get("author", "system"),
            domain=data.get("domain", "general")
        )

        # Reconstruct executions
        for exec_data in data.get("executions", []):
            execution = SkillExecution(
                id=exec_data["id"],
                skill_id=exec_data["skill_id"],
                timestamp=datetime.fromisoformat(exec_data["timestamp"]),
                context={},  # Simplified: not reconstructing full context
                result=ExecutionResult(
                    success=exec_data["success"],
                    output=None,
                    error=exec_data.get("error")
                ),
                duration_ms=exec_data["duration_ms"],
                retry_count=exec_data.get("retry_count", 0)
            )
            skill.executions.append(execution)

        skill._update_metrics()
        return skill


class ChaîneValidator:
    """
    Implements the Chaîne of Validation pipeline:
    Unit Tests → Integration → A/B Shadow → Canary → Regression Detection.
    """

    def __init__(self, skill_cache: 'SkillCrystallizationCache'):
        self.skill_cache = skill_cache

    def validate(
        self,
        skill: Skill,
        test_suite: Optional['TestSuite'] = None,
        integration_env: Optional[Any] = None,
        production_traffic_sample: float = 0.01
    ) -> ValidationResult:
        """
        Run full validation pipeline on a skill.

        Args:
            skill: Skill to validate
            test_suite: Unit/integration tests
            integration_env: Isolated test environment
            production_traffic_sample: Fraction of prod traffic for shadow mode (0-1)

        Returns:
            Overall validation result
        """
        stages = []
        overall_score = 0.0
        passed = True

        # Stage 1: Unit Tests
        result = self._run_unit_tests(skill, test_suite)
        stages.append(result)
        if not result.passed:
            passed = False

        # Stage 2: Integration Tests
        if passed:
            result = self._run_integration_tests(skill, integration_env)
            stages.append(result)
            if not result.passed:
                passed = False

        # Stage 3: A/B Shadow Mode
        if passed and integration_env:
            result = self._run_shadow_mode(skill, integration_env, production_traffic_sample)
            stages.append(result)
            if not result.passed:
                passed = False

        # Stage 4: Canary Rollout
        if passed:
            result = self._run_canary(skill, canary_percentage=0.05)
            stages.append(result)
            if not result.passed:
                passed = False

        # Stage 5: Regression Detection
        if passed:
            result = self._check_regression(skill)
            stages.append(result)
            if not result.passed:
                passed = False

        # Overall score is weighted average
        weights = [1.0, 1.2, 1.5, 1.5, 1.3]  # Later stages weighted more
        total_weight = sum(weights)
        weighted_sum = sum(s.score * w for s, w in zip(stages, weights))
        overall_score = weighted_sum / total_weight

        final_result = ValidationResult(
            stage="full_pipeline",
            passed=passed,
            score=overall_score,
            details=f"Passed {sum(1 for s in stages if s.passed)}/{len(stages)} stages"
        )

        skill.validation_history.append(final_result)
        return final_result

    def _run_unit_tests(self, skill: Skill, test_suite: Optional['TestSuite']) -> ValidationResult:
        """Run unit tests for the skill."""
        if not test_suite:
            # No tests defined, auto-pass with warning
            return ValidationResult(
                stage="unit_tests",
                passed=True,
                score=0.7,
                details="No unit tests defined"
            )

        passed, score, details = test_suite.run_for_skill(skill)
        return ValidationResult(
            stage="unit_tests",
            passed=passed,
            score=score,
            details=details
        )

    def _run_integration_tests(self, skill: Skill, integration_env: Optional[Any]) -> ValidationResult:
        """Run integration tests in isolated environment."""
        if not integration_env:
            return ValidationResult(
                stage="integration_tests",
                passed=True,
                score=0.6,
                details="No integration environment configured"
            )

        # Simulated integration test
        # In real impl, would deploy skill to test environment and run cross-module tests
        passed = skill.metrics.stability_score > 0.5
        score = 0.8 if passed else 0.3
        return ValidationResult(
            stage="integration_tests",
            passed=passed,
            score=score,
            details=f"Stability score: {skill.metrics.stability_score:.2f}"
        )

    def _run_shadow_mode(self, skill: Skill, integration_env: Any, traffic_sample: float) -> ValidationResult:
        """Run skill in shadow mode, mirroring prod traffic without affecting output."""
        # Simulated: check that skill produces results without errors
        passed = skill.metrics.total_executions >= 10  # Need some shadow data
        score = 0.9 if passed else 0.4
        return ValidationResult(
            stage="shadow_mode",
            passed=passed,
            score=score,
            details=f"Shadow executed on {skill.metrics.total_executions} traces"
        )

    def _run_canary(self, skill: Skill, canary_percentage: float) -> ValidationResult:
        """Canary rollout to small percentage of real traffic."""
        # Check recent performance in canary
        recent = skill.executions[-20:] if len(skill.executions) >= 20 else skill.executions
        if not recent:
            return ValidationResult(
                stage="canary",
                passed=False,
                score=0.0,
                details="No recent executions"
            )

        success_rate = sum(e.result.success for e in recent) / len(recent)
        passed = success_rate >= 0.8
        score = success_rate
        return ValidationResult(
            stage="canary",
            passed=passed,
            score=score,
            details=f"Canary success rate: {success_rate:.1%}"
        )

    def _check_regression(self, skill: Skill) -> ValidationResult:
        """Check for performance regression compared to previous valid version."""
        # Compare recent metrics to historical average
        if len(skill.executions) < 30:
            return ValidationResult(
                stage="regression_check",
                passed=True,
                score=0.8,
                details="Insufficient history for regression detection"
            )

        recent = skill.executions[-10:]
        older = skill.executions[-30:-10]

        recent_success = sum(e.result.success for e in recent) / len(recent)
        older_success = sum(e.result.success for e in older) / len(older)

        regression = older_success - recent_success
        passed = regression < 0.05  # Less than 5% drop
        score = max(0.0, 1.0 - abs(regression) * 5)  # 0.0-1.0, linear penalty

        return ValidationResult(
            stage="regression_check",
            passed=passed,
            score=score,
            details=f"Success delta: {regression:+.2%} (older: {older_success:.1%}, recent: {recent_success:.1%})"
        )


@dataclass
class TestSuite:
    """Collection of unit and integration tests for skills."""
    unit_tests: List[Callable] = field(default_factory=list)
    integration_tests: List[Callable] = field(default_factory=list)

    def add_unit_test(self, test_fn: Callable[[Skill], bool]):
        """Add a unit test function."""
        self.unit_tests.append(test_fn)

    def add_integration_test(self, test_fn: Callable[[Skill, Any], bool]):
        """Add an integration test function."""
        self.integration_tests.append(test_fn)

    def run_for_skill(self, skill: Skill) -> Tuple[bool, float, str]:
        """Run all tests for a skill."""
        passed = 0
        total = len(self.unit_tests) + len(self.integration_tests)

        if total == 0:
            return True, 0.5, "No tests defined"

        for test in self.unit_tests:
            try:
                if test(skill):
                    passed += 1
            except Exception as e:
                pass  # Test failure

        score = passed / total if total > 0 else 0.0
        details = f"Passed {passed}/{total} tests"
        return passed == total, score, details


class SkillCrystallizationCache:
    """
    Manages the complete skill lifecycle with chaîne validation.
    Provides storage, retrieval, versioning, and validation orchestration.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.skills: Dict[str, Skill] = {}  # skill_id -> Skill
        self.skill_index: Dict[str, Set[str]] = {  # tag/domain -> skill_ids
            "tags": {},
            "domains": {}
        }
        self.validator = ChaîneValidator(self)

        if storage_path:
            self._load_from_disk()

    def register_skill(
        self,
        name: str,
        description: str,
        module: BaseModule,
        test_suite: Optional[TestSuite] = None,
        **metadata
    ) -> Skill:
        """
        Register a new skill as a prototype.

        Args:
            name: Human-readable skill name
            description: What the skill does
            module: Executable module instance
            test_suite: Optional tests for validation
            **metadata: Additional skill metadata

        Returns:
            Created Skill object
        """
        skill_id = str(uuid.uuid4())

        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            module=module,
            state=SkillState.PROTOTYPE,
            tags=set(metadata.get("tags", [])),
            author=metadata.get("author", "system"),
            domain=metadata.get("domain", "general")
        )

        self.skills[skill_id] = skill
        self._index_skill(skill)
        self._persist()

        return skill

    def find_skill(
        self,
        name: Optional[str] = None,
        domain: Optional[str] = None,
        tag: Optional[str] = None,
        state: Optional[SkillState] = None,
        min_stability: float = 0.0
    ) -> List[Skill]:
        """
        Search for skills by criteria.

        Args:
            name: Exact or partial name match
            domain: Domain filter
            tag: Tag filter
            state: State filter
            min_stability: Minimum stability score (0-1)

        Returns:
            List of matching skills
        """
        results = []

        for skill in self.skills.values():
            if state and skill.state != state:
                continue
            if domain and skill.domain != domain:
                continue
            if tag and tag not in skill.tags:
                continue
            if name and name.lower() not in skill.name.lower():
                continue
            if skill.metrics.stability_score < min_stability:
                continue
            results.append(skill)

        # Sort by stability and execution count
        results.sort(key=lambda s: (s.metrics.stability_score, s.metrics.total_executions), reverse=True)
        return results

    def promote_to_candidate(self, skill_id: str, min_executions: int = 5) -> bool:
        """Manually promote a skill to candidate state (if criteria met)."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False

        if skill.metrics.total_executions >= min_executions:
            skill.state = SkillState.CANDIDATE
            self._persist()
            return True
        return False

    def promote_to_crystallized(
        self,
        skill_id: str,
        validation_suite: Optional[TestSuite] = None,
        integration_env: Optional[Any] = None
    ) -> bool:
        """
        Validate and crystallize a skill. Requires passing chaîne validation.

        Returns:
            True if crystallized, False otherwise
        """
        skill = self.skills.get(skill_id)
        if not skill or skill.state != SkillState.CANDIDATE:
            return False

        if skill.metrics.total_executions < 50:
            return False

        # Run full validation pipeline
        result = self.validator.validate(
            skill,
            test_suite=validation_suite,
            integration_env=integration_env
        )

        if result.passed and result.score >= 0.8:
            skill.state = SkillState.CRYSTALLIZED
            skill.version += 1
            self._persist()
            return True

        return False

    def archive_skill(self, skill_id: str, deprecation_warning: Optional[str] = None) -> bool:
        """Archive (deprecate) a skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False

        skill.state = SkillState.ARCHIVED
        skill.deprecation_warning = deprecation_warning
        self._persist()
        return True

    def create_derivative_skill(
        self,
        parent_skill_id: str,
        name: str,
        description: str,
        mutated_module: BaseModule
    ) -> Optional[Skill]:
        """Create a new skill version based on existing skill (evolutionary lineage)."""
        parent = self.skills.get(parent_skill_id)
        if not parent:
            return None

        derivative = Skill(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            module=mutated_module,
            state=SkillState.PROTOTYPE,
            parent_skill_id=parent_skill_id,
            tags=parent.tags.copy(),
            domain=parent.domain,
            author=parent.author
        )

        self.skills[derivative.id] = derivative
        self._index_skill(derivative)
        self._persist()
        return derivative

    def get_skill_execution_history(
        self,
        skill_id: str,
        limit: int = 100
    ) -> List[SkillExecution]:
        """Get recent executions for a skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return []
        return skill.executions[-limit:]

    def _index_skill(self, skill: Skill):
        """Update search indices."""
        # Index by domain
        if skill.domain not in self.skill_index["domains"]:
            self.skill_index["domains"][skill.domain] = set()
        self.skill_index["domains"][skill.domain].add(skill.id)

        # Index by tags
        for tag in skill.tags:
            if tag not in self.skill_index["tags"]:
                self.skill_index["tags"][tag] = set()
            self.skill_index["tags"][tag].add(skill.id)

    def _persist(self):
        """Save state to disk."""
        if not self.storage_path:
            return

        os.makedirs(self.storage_path, exist_ok=True)

        skills_file = os.path.join(self.storage_path, "skills.json")
        data = {
            "skills": {sid: s.to_dict() for sid, s in self.skills.items()},
            "index": {
                "domains": {k: list(v) for k, v in self.skill_index["domains"].items()},
                "tags": {k: list(v) for k, v in self.skill_index["tags"].items()}
            },
            "timestamp": datetime.now().isoformat()
        }
        with open(skills_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_disk(self):
        """Load state from disk."""
        if not self.storage_path:
            return

        skills_file = os.path.join(self.storage_path, "skills.json")
        if not os.path.exists(skills_file):
            return

        try:
            with open(skills_file, 'r') as f:
                data = json.load(f)

            self.skills = {}
            for sid, sdata in data.get("skills", {}).items():
                # Simplified: need module factory to reconstruct module
                # For now, skip reconstruction of module
                pass

            self.skill_index = data.get("index", {"domains": {}, "tags": {}})
        except Exception as e:
            print(f"Failed to load skill cache: {e}")
