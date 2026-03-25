"""Unit tests for FitnessLedger.

Covers:
- cache hit: lookup returns cached entry and skips re-evaluation
- cache miss: lookup returns None, evaluation runs and records result
- persistence round-trip: save/load preserves all entry fields
- evaluate_genome integration: ledger param wires correctly into FitnessEvaluator
"""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

# Import FitnessLedger directly to avoid evoforge/__init__ chain issues
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))
from evoforge.core.fitness_ledger import FitnessLedger, LedgerEntry, compute_genome_hash


def _make_genome(config=None):
    """Return a minimal mock genome."""
    genome = MagicMock()
    genome.config = config or {"planning": {"algorithm": "react"}, "memory": {"strategy": "simple"}}
    return genome


class TestLedgerLookup(unittest.TestCase):
    """cache miss and cache hit paths."""

    def setUp(self):
        self.ledger = FitnessLedger()

    def test_miss_returns_none(self):
        result = self.ledger.lookup("nonexistent_hash")
        self.assertIsNone(result)

    def test_miss_increments_miss_counter(self):
        self.ledger.lookup("abc123")
        self.assertEqual(self.ledger.stats()["misses"], 1)
        self.assertEqual(self.ledger.stats()["hits"], 0)

    def test_hit_returns_entry(self):
        self.ledger.record("abc123", best_score=0.75)
        entry = self.ledger.lookup("abc123")
        self.assertIsNotNone(entry)
        self.assertIsInstance(entry, LedgerEntry)
        self.assertEqual(entry.best_score, 0.75)

    def test_hit_increments_hit_counter(self):
        self.ledger.record("abc123", best_score=0.5)
        self.ledger.lookup("abc123")
        stats = self.ledger.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 0)

    def test_hit_rate_after_mix(self):
        self.ledger.record("h1", best_score=0.9)
        self.ledger.lookup("h1")   # hit
        self.ledger.lookup("h2")   # miss
        stats = self.ledger.stats()
        self.assertAlmostEqual(stats["hit_rate"], 0.5)


class TestLedgerRecord(unittest.TestCase):
    """record() creates and updates entries correctly."""

    def setUp(self):
        self.ledger = FitnessLedger()

    def test_record_creates_entry(self):
        entry = self.ledger.record("h1", best_score=0.6)
        self.assertEqual(entry.genome_hash, "h1")
        self.assertEqual(entry.best_score, 0.6)
        self.assertEqual(entry.evaluation_count, 1)

    def test_record_stores_pareto_metrics(self):
        entry = self.ledger.record(
            "h1", best_score=0.6,
            pareto_metrics={"task_completion_rate": 0.8, "token_efficiency": 0.7},
        )
        self.assertEqual(entry.pareto_metrics["task_completion_rate"], 0.8)

    def test_record_stores_lineage_fields(self):
        entry = self.ledger.record(
            "h2", best_score=0.5,
            parent_genome_hash="h1",
            mutation_applied="param_mutation:planning.algorithm",
        )
        self.assertEqual(entry.parent_genome_hash, "h1")
        self.assertEqual(entry.mutation_applied, "param_mutation:planning.algorithm")

    def test_duplicate_record_increments_count(self):
        self.ledger.record("h1", best_score=0.5)
        self.ledger.record("h1", best_score=0.4)  # lower score
        entry = self.ledger.lookup("h1")
        self.assertEqual(entry.evaluation_count, 2)

    def test_duplicate_record_updates_score_if_higher(self):
        self.ledger.record("h1", best_score=0.5)
        self.ledger.record("h1", best_score=0.9)
        entry = self.ledger.lookup("h1")
        self.assertAlmostEqual(entry.best_score, 0.9)

    def test_duplicate_record_keeps_score_if_lower(self):
        self.ledger.record("h1", best_score=0.8)
        self.ledger.record("h1", best_score=0.3)
        entry = self.ledger.lookup("h1")
        self.assertAlmostEqual(entry.best_score, 0.8)


class TestLedgerLineage(unittest.TestCase):
    """get_lineage() walks parent chain oldest-first."""

    def setUp(self):
        self.ledger = FitnessLedger()
        self.ledger.record("root", best_score=0.5)
        self.ledger.record("child", best_score=0.6, parent_genome_hash="root")
        self.ledger.record("grandchild", best_score=0.7, parent_genome_hash="child")

    def test_lineage_oldest_first(self):
        chain = self.ledger.get_lineage("grandchild")
        self.assertEqual([e.genome_hash for e in chain], ["root", "child", "grandchild"])

    def test_lineage_single_entry(self):
        chain = self.ledger.get_lineage("root")
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0].genome_hash, "root")

    def test_lineage_unknown_hash(self):
        chain = self.ledger.get_lineage("unknown")
        self.assertEqual(chain, [])


class TestLedgerPersistence(unittest.TestCase):
    """save/load round-trip preserves all LedgerEntry fields."""

    def _make_populated_ledger(self):
        ledger = FitnessLedger()
        ledger.record(
            "aabbccdd",
            best_score=0.83,
            parent_genome_hash="00000000",
            mutation_applied="crossover",
            battery_scores={"task_a": 0.9, "task_b": 0.75},
            pareto_metrics={"task_completion_rate": 0.83, "token_efficiency": 0.6},
        )
        ledger.record("eeff0011", best_score=0.55)
        return ledger

    def test_round_trip_entry_count(self):
        ledger = self._make_populated_ledger()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ledger.save(path)
            loaded = FitnessLedger()
            loaded.load(path)
            self.assertEqual(loaded.stats()["entries"], 2)
        finally:
            os.unlink(path)

    def test_round_trip_preserves_all_fields(self):
        ledger = self._make_populated_ledger()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ledger.save(path)
            loaded = FitnessLedger()
            loaded.load(path)
            entry = loaded.lookup("aabbccdd")
            self.assertIsNotNone(entry)
            self.assertAlmostEqual(entry.best_score, 0.83)
            self.assertEqual(entry.parent_genome_hash, "00000000")
            self.assertEqual(entry.mutation_applied, "crossover")
            self.assertEqual(entry.battery_scores["task_a"], 0.9)
            self.assertEqual(entry.pareto_metrics["task_completion_rate"], 0.83)
            self.assertEqual(entry.evaluation_count, 1)
        finally:
            os.unlink(path)

    def test_round_trip_json_is_valid(self):
        ledger = self._make_populated_ledger()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ledger.save(path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("aabbccdd", data)
        finally:
            os.unlink(path)

    def test_load_merges_into_existing(self):
        ledger_a = FitnessLedger()
        ledger_a.record("h1", best_score=0.5)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ledger_a.save(path)
            ledger_b = FitnessLedger()
            ledger_b.record("h2", best_score=0.9)
            ledger_b.load(path)
            self.assertEqual(ledger_b.stats()["entries"], 2)
        finally:
            os.unlink(path)


class TestComputeGenomeHash(unittest.TestCase):
    """compute_genome_hash produces stable, collision-resistant keys."""

    def test_same_config_same_hash(self):
        g1 = _make_genome({"a": 1, "b": 2})
        g2 = _make_genome({"a": 1, "b": 2})
        self.assertEqual(compute_genome_hash(g1), compute_genome_hash(g2))

    def test_different_config_different_hash(self):
        g1 = _make_genome({"a": 1})
        g2 = _make_genome({"a": 2})
        self.assertNotEqual(compute_genome_hash(g1), compute_genome_hash(g2))

    def test_hash_is_16_chars(self):
        g = _make_genome()
        self.assertEqual(len(compute_genome_hash(g)), 16)

    def test_key_order_ignored(self):
        g1 = _make_genome({"x": 1, "y": 2})
        g2 = _make_genome({"y": 2, "x": 1})
        self.assertEqual(compute_genome_hash(g1), compute_genome_hash(g2))


class TestFitnessEvaluatorLedgerIntegration(unittest.TestCase):
    """FitnessEvaluator.evaluate_genome ledger param integration."""

    def setUp(self):
        # Import here to bypass any top-level import issues in the evoforge package
        from evoforge.evolution.fitness import FitnessEvaluator
        self.evaluator = FitnessEvaluator()
        self.ledger = FitnessLedger()

    def test_cache_miss_records_entry(self):
        genome = _make_genome()
        self.evaluator.evaluate_genome(genome, ledger=self.ledger)
        ghash = compute_genome_hash(genome)
        entry = self.ledger.lookup(ghash)
        self.assertIsNotNone(entry)
        self.assertGreater(entry.best_score, 0.0)

    def test_cache_hit_skips_evaluation(self):
        genome = _make_genome()
        # Pre-populate ledger with a known score
        ghash = compute_genome_hash(genome)
        self.ledger.record(ghash, best_score=0.99,
                           pareto_metrics={"token_efficiency": 0.1,
                                           "compute_efficiency": 0.2,
                                           "reasoning_quality": 0.3})

        # evaluate_genome should return ledger entry without re-evaluating
        metrics = self.evaluator.evaluate_genome(genome, ledger=self.ledger)
        self.assertAlmostEqual(metrics.task_success_rate, 0.99)
        # Stats: 1 hit from evaluate_genome lookup, 1 hit from test record lookup
        self.assertGreaterEqual(self.ledger.stats()["hits"], 1)

    def test_no_ledger_behaves_as_before(self):
        genome = _make_genome()
        # No ledger — should not raise and should return valid metrics
        metrics = self.evaluator.evaluate_genome(genome)
        self.assertIsNotNone(metrics)
        self.assertGreaterEqual(metrics.task_success_rate, 0.0)

    def test_second_call_is_cache_hit(self):
        genome = _make_genome()
        self.evaluator.evaluate_genome(genome, ledger=self.ledger)
        self.evaluator.evaluate_genome(genome, ledger=self.ledger)
        stats = self.ledger.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)


if __name__ == "__main__":
    unittest.main()
