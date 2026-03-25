"""Unit tests for ValidationBattery.

Covers:
- Task loading: ValidationBattery.load() deserialises JSON correctly
- Scoring functions: exact_match, numeric_match, contains, boolean_match
- Execution stub: run() with infer_fn returns correct BatteryResult
- Simulation path: run() without infer_fn uses genome-config heuristics
- Result serialization: BatteryResult.to_pareto_metrics() returns expected keys
- FitnessEvaluator integration: battery= param wires into evaluate_genome()
- Backward compat: FitnessEvaluator without battery still uses _simulate_*
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

from evoforge.core.validation_battery import (
    ValidationBattery,
    ValidationTask,
    ValidationResult,
    BatteryResult,
    _score_exact_match,
    _score_numeric_match,
    _score_contains,
    _score_boolean_match,
)
from evoforge.evolution.fitness import FitnessEvaluator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_genome(config=None):
    genome = MagicMock()
    genome.config = config or {"planning": {"algorithm": "react"}, "memory": {"strategy": "simple"}}
    return genome


def _make_tasks(n=5):
    """Return *n* minimal ValidationTask objects."""
    return [
        ValidationTask(
            task_id=f"t_{i:03d}",
            category="math",
            prompt=f"Prompt {i}",
            expected_answer=str(i),
            scoring_fn="numeric_match",
            difficulty=1.0,
        )
        for i in range(n)
    ]


def _battery_from_tasks(tasks):
    return ValidationBattery(tasks=tasks)


def _write_battery_json(tasks_dicts, tmpdir):
    path = os.path.join(tmpdir, "battery.json")
    with open(path, "w") as f:
        json.dump(tasks_dicts, f)
    return path


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

class TestScoringFunctions(unittest.TestCase):

    # exact_match
    def test_exact_match_identical(self):
        self.assertTrue(_score_exact_match("hello", "hello"))

    def test_exact_match_case_insensitive(self):
        self.assertTrue(_score_exact_match("Hello", "hello"))

    def test_exact_match_fails_on_different(self):
        self.assertFalse(_score_exact_match("hello", "world"))

    def test_exact_match_strips_whitespace(self):
        self.assertTrue(_score_exact_match("  yes  ", "yes"))

    # numeric_match
    def test_numeric_match_integers(self):
        self.assertTrue(_score_numeric_match("42", "42"))

    def test_numeric_match_floats(self):
        self.assertTrue(_score_numeric_match("3.14", "3.14"))

    def test_numeric_match_tolerance(self):
        self.assertTrue(_score_numeric_match("12.5", "12.500000"))

    def test_numeric_match_fails_on_different(self):
        self.assertFalse(_score_numeric_match("12", "13"))

    def test_numeric_match_non_numeric_returns_false(self):
        self.assertFalse(_score_numeric_match("abc", "12"))

    # contains
    def test_contains_substring_present(self):
        self.assertTrue(_score_contains("the quick brown fox", "quick"))

    def test_contains_case_insensitive(self):
        self.assertTrue(_score_contains("Hello World", "hello"))

    def test_contains_fails_when_absent(self):
        self.assertFalse(_score_contains("hello", "world"))

    # boolean_match
    def test_boolean_match_true_variants(self):
        for v in ("true", "yes", "correct"):
            with self.subTest(v=v):
                self.assertTrue(_score_boolean_match(v, "true"))

    def test_boolean_match_false_variants(self):
        for v in ("false", "no", "incorrect"):
            with self.subTest(v=v):
                self.assertTrue(_score_boolean_match(v, "false"))

    def test_boolean_match_mismatch(self):
        self.assertFalse(_score_boolean_match("yes", "false"))


# ---------------------------------------------------------------------------
# ValidationTask.check()
# ---------------------------------------------------------------------------

class TestValidationTaskCheck(unittest.TestCase):

    def test_check_exact_pass(self):
        task = ValidationTask("t1", "math", "p", "12", "exact_match")
        self.assertTrue(task.check("12"))

    def test_check_exact_fail(self):
        task = ValidationTask("t1", "math", "p", "12", "exact_match")
        self.assertFalse(task.check("13"))

    def test_check_numeric_pass(self):
        task = ValidationTask("t1", "math", "p", "12.5", "numeric_match")
        self.assertTrue(task.check("12.5"))

    def test_check_unknown_scoring_fn_falls_back_to_exact(self):
        task = ValidationTask("t1", "math", "p", "yes", "nonexistent_fn")
        self.assertTrue(task.check("yes"))


# ---------------------------------------------------------------------------
# ValidationBattery.load()
# ---------------------------------------------------------------------------

class TestValidationBatteryLoad(unittest.TestCase):

    def _sample_json(self):
        return [
            {
                "id": "math_001",
                "category": "math",
                "prompt": "What is 1+1?",
                "expected_answer": "2",
                "scoring_fn": "numeric_match",
                "difficulty": 1.0,
            },
            {
                "id": "lang_001",
                "category": "language",
                "prompt": "Past tense of go?",
                "expected_answer": "went",
                "scoring_fn": "exact_match",
                # no difficulty — should use category default
            },
        ]

    def test_load_task_count(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_battery_json(self._sample_json(), d)
            battery = ValidationBattery.load(path)
        self.assertEqual(len(battery.tasks), 2)

    def test_load_task_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_battery_json(self._sample_json(), d)
            battery = ValidationBattery.load(path)
        t = battery.tasks[0]
        self.assertEqual(t.task_id, "math_001")
        self.assertEqual(t.category, "math")
        self.assertEqual(t.expected_answer, "2")
        self.assertEqual(t.scoring_fn, "numeric_match")
        self.assertEqual(t.difficulty, 1.0)

    def test_load_default_difficulty_from_category(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_battery_json(self._sample_json(), d)
            battery = ValidationBattery.load(path)
        lang_task = battery.tasks[1]
        # language default difficulty is 0.9
        self.assertAlmostEqual(lang_task.difficulty, 0.9)

    def test_load_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            ValidationBattery.load("/nonexistent/path/battery.json")

    def test_load_real_battery_v1(self):
        repo_root = os.path.join(os.path.dirname(__file__), '../../../../')
        path = os.path.join(repo_root, "evoforge/data/battery_v1.json")
        battery = ValidationBattery.load(path)
        self.assertEqual(len(battery.tasks), 30)
        categories = {t.category for t in battery.tasks}
        self.assertIn("math", categories)
        self.assertIn("code", categories)
        self.assertIn("logic", categories)
        self.assertIn("language", categories)


# ---------------------------------------------------------------------------
# ValidationBattery.run() with infer_fn stub
# ---------------------------------------------------------------------------

class TestValidationBatteryRunWithInferFn(unittest.TestCase):

    def setUp(self):
        self.tasks = _make_tasks(5)
        self.battery = _battery_from_tasks(self.tasks)
        self.genome = _make_genome()

    def test_all_correct_infer_fn(self):
        # infer_fn always returns the correct answer
        def always_correct(task_id, prompt):
            for t in self.tasks:
                if t.task_id == task_id:
                    return t.expected_answer
            return "__wrong__"

        result = self.battery.run(self.genome, infer_fn=always_correct)
        self.assertAlmostEqual(result.task_completion_rate, 1.0)
        self.assertAlmostEqual(result.reasoning_quality, 1.0)

    def test_all_wrong_infer_fn(self):
        def always_wrong(task_id, prompt):
            return "__wrong__"

        result = self.battery.run(self.genome, infer_fn=always_wrong)
        self.assertAlmostEqual(result.task_completion_rate, 0.0)
        self.assertAlmostEqual(result.reasoning_quality, 0.0)

    def test_partial_correct_infer_fn(self):
        # First 2 correct, last 3 wrong
        correct_ids = {self.tasks[0].task_id, self.tasks[1].task_id}

        def partial(task_id, prompt):
            for t in self.tasks:
                if t.task_id == task_id and task_id in correct_ids:
                    return t.expected_answer
            return "__wrong__"

        result = self.battery.run(self.genome, infer_fn=partial)
        self.assertAlmostEqual(result.task_completion_rate, 2 / 5)

    def test_run_returns_battery_result(self):
        result = self.battery.run(self.genome, infer_fn=lambda tid, p: "__wrong__")
        self.assertIsInstance(result, BatteryResult)

    def test_run_raw_results_length(self):
        result = self.battery.run(self.genome, infer_fn=lambda tid, p: "__wrong__")
        self.assertEqual(len(result.raw_results), 5)

    def test_run_raw_results_have_latency(self):
        result = self.battery.run(self.genome, infer_fn=lambda tid, p: "__wrong__")
        for r in result.raw_results:
            self.assertGreaterEqual(r.latency_ms, 0.0)

    def test_token_efficiency_clamped(self):
        result = self.battery.run(self.genome, infer_fn=lambda tid, p: "__wrong__")
        self.assertGreaterEqual(result.token_efficiency, 0.0)
        self.assertLessEqual(result.token_efficiency, 1.0)


# ---------------------------------------------------------------------------
# ValidationBattery.run() simulation path (no infer_fn)
# ---------------------------------------------------------------------------

class TestValidationBatterySimulation(unittest.TestCase):

    def setUp(self):
        repo_root = os.path.join(os.path.dirname(__file__), '../../../../')
        path = os.path.join(repo_root, "evoforge/data/battery_v1.json")
        self.battery = ValidationBattery.load(path)

    def test_simulation_is_deterministic(self):
        genome = _make_genome({"planning": {"algorithm": "chain_of_thought"}})
        r1 = self.battery.run(genome)
        r2 = self.battery.run(genome)
        self.assertAlmostEqual(r1.task_completion_rate, r2.task_completion_rate)

    def test_simulation_tree_of_thoughts_beats_react(self):
        genome_tot = _make_genome({"planning": {"algorithm": "tree_of_thoughts"}})
        genome_react = _make_genome({"planning": {"algorithm": "react"}})
        r_tot = self.battery.run(genome_tot)
        r_react = self.battery.run(genome_react)
        # tree_of_thoughts should have higher or equal task_completion_rate
        self.assertGreaterEqual(r_tot.task_completion_rate, r_react.task_completion_rate)

    def test_simulation_returns_valid_ranges(self):
        genome = _make_genome()
        result = self.battery.run(genome)
        self.assertGreaterEqual(result.task_completion_rate, 0.0)
        self.assertLessEqual(result.task_completion_rate, 1.0)
        self.assertGreaterEqual(result.reasoning_quality, 0.0)
        self.assertLessEqual(result.reasoning_quality, 1.0)


# ---------------------------------------------------------------------------
# BatteryResult.to_pareto_metrics()
# ---------------------------------------------------------------------------

class TestBatteryResultParetoMetrics(unittest.TestCase):

    def _make_result(self, tcr=0.7, rq=0.65, te=0.5):
        return BatteryResult(
            task_completion_rate=tcr,
            reasoning_quality=rq,
            token_efficiency=te,
        )

    def test_to_pareto_metrics_keys(self):
        metrics = self._make_result().to_pareto_metrics()
        self.assertIn("task_completion_rate", metrics)
        self.assertIn("reasoning_quality", metrics)
        self.assertIn("token_efficiency", metrics)

    def test_to_pareto_metrics_values(self):
        result = self._make_result(0.8, 0.75, 0.6)
        metrics = result.to_pareto_metrics()
        self.assertAlmostEqual(metrics["task_completion_rate"], 0.8)
        self.assertAlmostEqual(metrics["reasoning_quality"], 0.75)
        self.assertAlmostEqual(metrics["token_efficiency"], 0.6)

    def test_to_pareto_metrics_returns_dict(self):
        self.assertIsInstance(self._make_result().to_pareto_metrics(), dict)


# ---------------------------------------------------------------------------
# FitnessEvaluator integration
# ---------------------------------------------------------------------------

class TestFitnessEvaluatorBatteryIntegration(unittest.TestCase):

    def _make_battery_with_fixed_result(self, tcr, rq, te):
        """Return a ValidationBattery whose run() returns fixed metrics."""
        battery = MagicMock(spec=ValidationBattery)
        battery.run.return_value = BatteryResult(
            task_completion_rate=tcr,
            reasoning_quality=rq,
            token_efficiency=te,
        )
        return battery

    def test_battery_result_feeds_into_fitness_metrics(self):
        battery = self._make_battery_with_fixed_result(0.9, 0.85, 0.7)
        evaluator = FitnessEvaluator(battery=battery)
        genome = _make_genome()
        metrics = evaluator.evaluate_genome(genome)
        self.assertAlmostEqual(metrics.task_success_rate, 0.9)
        self.assertAlmostEqual(metrics.interpretability, 0.85)
        # sample_efficiency = 1 - token_efficiency
        self.assertAlmostEqual(metrics.sample_efficiency, 1.0 - 0.7)

    def test_battery_arg_on_evaluate_genome_overrides_self_battery(self):
        """battery kwarg on evaluate_genome takes precedence over self.battery."""
        self_battery = self._make_battery_with_fixed_result(0.5, 0.5, 0.5)
        call_battery = self._make_battery_with_fixed_result(0.9, 0.85, 0.7)
        evaluator = FitnessEvaluator(battery=self_battery)
        genome = _make_genome()
        metrics = evaluator.evaluate_genome(genome, battery=call_battery)
        self.assertAlmostEqual(metrics.task_success_rate, 0.9)
        self_battery.run.assert_not_called()
        call_battery.run.assert_called_once()

    def test_no_battery_falls_back_to_simulation(self):
        """Without battery, _simulate_* heuristics are used (backward compat)."""
        evaluator = FitnessEvaluator()
        genome = _make_genome()
        metrics = evaluator.evaluate_genome(genome)
        # Simulation yields task_success_rate in [0, 1]
        self.assertGreaterEqual(metrics.task_success_rate, 0.0)
        self.assertLessEqual(metrics.task_success_rate, 1.0)

    def test_battery_called_with_genome(self):
        battery = self._make_battery_with_fixed_result(0.7, 0.6, 0.5)
        evaluator = FitnessEvaluator(battery=battery)
        genome = _make_genome()
        evaluator.evaluate_genome(genome)
        battery.run.assert_called_once_with(genome)

    def test_ledger_cache_hit_skips_battery(self):
        """When ledger has a cache hit, battery.run() must not be called."""
        from evoforge.core.fitness_ledger import FitnessLedger, compute_genome_hash

        battery = self._make_battery_with_fixed_result(0.9, 0.85, 0.7)
        ledger = FitnessLedger()
        genome = _make_genome()
        ghash = compute_genome_hash(genome)
        ledger.record(ghash, best_score=0.8, pareto_metrics={"token_efficiency": 0.5, "compute_efficiency": 0.4, "reasoning_quality": 0.6})

        evaluator = FitnessEvaluator(battery=battery)
        evaluator.evaluate_genome(genome, ledger=ledger)
        battery.run.assert_not_called()


# ---------------------------------------------------------------------------
# FitnessEvaluator.is_battery_improving() acceptance gate
# ---------------------------------------------------------------------------

class TestIsBatteryImproving(unittest.TestCase):
    """Acceptance gate: battery_score must improve over 3 consecutive runs."""

    def _make_ledger_with_chain(self, scores):
        """Build a FitnessLedger with a parent chain matching *scores* (oldest first)."""
        from evoforge.core.fitness_ledger import FitnessLedger, compute_genome_hash
        ledger = FitnessLedger()
        prev_hash = ""
        hashes = [f"genome_{i:04d}" for i in range(len(scores))]
        for i, (gh, score) in enumerate(zip(hashes, scores)):
            ledger.record(
                gh,
                best_score=score,
                parent_genome_hash=prev_hash,
                pareto_metrics={"task_completion_rate": score},
            )
            prev_hash = gh
        return ledger, hashes[-1]  # ledger + tip genome hash

    def test_monotone_improvement_returns_true(self):
        evaluator = FitnessEvaluator()
        genome = _make_genome()
        ledger, tip = self._make_ledger_with_chain([0.5, 0.6, 0.7, 0.8])
        # Patch compute_genome_hash to return our tip
        import evoforge.core.fitness_ledger as fl_mod
        orig = fl_mod.compute_genome_hash
        fl_mod.compute_genome_hash = lambda g: tip
        try:
            result = evaluator.is_battery_improving(genome, ledger, window=3)
        finally:
            fl_mod.compute_genome_hash = orig
        self.assertTrue(result)

    def test_flat_scores_returns_false(self):
        evaluator = FitnessEvaluator()
        genome = _make_genome()
        ledger, tip = self._make_ledger_with_chain([0.6, 0.6, 0.6, 0.6])
        import evoforge.core.fitness_ledger as fl_mod
        orig = fl_mod.compute_genome_hash
        fl_mod.compute_genome_hash = lambda g: tip
        try:
            result = evaluator.is_battery_improving(genome, ledger, window=3)
        finally:
            fl_mod.compute_genome_hash = orig
        self.assertFalse(result)

    def test_regression_returns_false(self):
        evaluator = FitnessEvaluator()
        genome = _make_genome()
        ledger, tip = self._make_ledger_with_chain([0.8, 0.7, 0.6, 0.5])
        import evoforge.core.fitness_ledger as fl_mod
        orig = fl_mod.compute_genome_hash
        fl_mod.compute_genome_hash = lambda g: tip
        try:
            result = evaluator.is_battery_improving(genome, ledger, window=3)
        finally:
            fl_mod.compute_genome_hash = orig
        self.assertFalse(result)

    def test_insufficient_history_returns_false(self):
        """Fewer than window+1 ancestors → not enough history."""
        evaluator = FitnessEvaluator()
        genome = _make_genome()
        ledger, tip = self._make_ledger_with_chain([0.6, 0.7])  # only 2 entries
        import evoforge.core.fitness_ledger as fl_mod
        orig = fl_mod.compute_genome_hash
        fl_mod.compute_genome_hash = lambda g: tip
        try:
            result = evaluator.is_battery_improving(genome, ledger, window=3)
        finally:
            fl_mod.compute_genome_hash = orig
        self.assertFalse(result)

    def test_partial_regression_breaks_gate(self):
        """Improvement then dip then improvement — gate must still fail."""
        evaluator = FitnessEvaluator()
        genome = _make_genome()
        ledger, tip = self._make_ledger_with_chain([0.5, 0.7, 0.6, 0.8])
        import evoforge.core.fitness_ledger as fl_mod
        orig = fl_mod.compute_genome_hash
        fl_mod.compute_genome_hash = lambda g: tip
        try:
            result = evaluator.is_battery_improving(genome, ledger, window=3)
        finally:
            fl_mod.compute_genome_hash = orig
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
