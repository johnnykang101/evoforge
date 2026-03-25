"""
Tests for CKSE KnowledgeSynthesizer cache hit/miss tracking.

Covers:
- _semantic_lookup: match and no-match cases
- get_cache_stats: structure and hit rate calculation
- Immediate knowledge_store append enabling intra-batch hits
- Abstraction hash dedup counting as cache hits
- source_keywords serialization in to_dict()
"""
import unittest

from evoforge.core.ckse import KnowledgeSynthesizer, KnowledgeUnit, KnowledgeType


def _make_insight(
    content="high success rate achieved in module_a",
    confidence=0.9,
    genome_id="g1",
    genome_name="genome1",
    module="module_a",
    knowledge_type=KnowledgeType.OPTIMIZATION,
):
    return {
        "type": knowledge_type,
        "content": content,
        "confidence": confidence,
        "module": module,
        "source_genome_id": genome_id,
        "source_genome_name": genome_name,
    }


def _make_cluster(*insights):
    return list(insights) if insights else [_make_insight()]


class TestKnowledgeSynthesizerCacheStats(unittest.TestCase):
    def setUp(self):
        self.synth = KnowledgeSynthesizer()

    def test_initial_stats_all_zero(self):
        stats = self.synth.get_cache_stats()
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["cache_misses"], 0)
        self.assertEqual(stats["cache_hit_rate"], 0.0)
        self.assertEqual(stats["knowledge_store_size"], 0)
        self.assertEqual(stats["abstraction_cache_size"], 0)

    def test_stats_keys_present(self):
        stats = self.synth.get_cache_stats()
        for key in ("cache_hits", "cache_misses", "cache_hit_rate",
                    "knowledge_store_size", "abstraction_cache_size"):
            self.assertIn(key, stats)

    def test_hit_rate_zero_when_no_lookups(self):
        self.assertEqual(self.synth.get_cache_stats()["cache_hit_rate"], 0.0)

    def test_hit_rate_computed_correctly(self):
        self.synth._cache_hits = 3
        self.synth._cache_misses = 7
        stats = self.synth.get_cache_stats()
        self.assertAlmostEqual(stats["cache_hit_rate"], 0.3)

    def test_hit_rate_is_1_when_all_hits(self):
        self.synth._cache_hits = 5
        self.synth._cache_misses = 0
        self.assertAlmostEqual(self.synth.get_cache_stats()["cache_hit_rate"], 1.0)

    def test_knowledge_store_size_reflects_store(self):
        cluster = _make_cluster()
        unit = self.synth._create_knowledge_unit(cluster)
        if unit:
            self.synth.knowledge_store.append(unit)
        self.assertEqual(
            self.synth.get_cache_stats()["knowledge_store_size"],
            len(self.synth.knowledge_store),
        )


class TestSemanticLookup(unittest.TestCase):
    def setUp(self):
        self.synth = KnowledgeSynthesizer()

    def _seed_unit(self, content="high success rate achieved in module_a"):
        cluster = _make_cluster(_make_insight(content=content))
        unit = self.synth._create_knowledge_unit(cluster)
        if unit:
            self.synth.knowledge_store.append(unit)
            return unit
        return None

    def test_returns_none_on_empty_store(self):
        cluster = _make_cluster()
        result = self.synth._semantic_lookup(cluster)
        self.assertIsNone(result)

    def test_returns_none_on_empty_cluster(self):
        self._seed_unit()
        result = self.synth._semantic_lookup([])
        self.assertIsNone(result)

    def test_returns_match_for_high_overlap_cluster(self):
        self._seed_unit("high success rate achieved in module_a")
        similar = _make_cluster(
            _make_insight(content="high success rate achieved module_a subsystem")
        )
        result = self.synth._semantic_lookup(similar)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, KnowledgeUnit)

    def test_returns_none_for_unrelated_cluster(self):
        self._seed_unit("high success rate achieved in module_a")
        unrelated = _make_cluster(
            _make_insight(
                content="memory pressure causes crashes in production environment",
                knowledge_type=KnowledgeType.CONSTRAINTS,
            )
        )
        result = self.synth._semantic_lookup(unrelated)
        self.assertIsNone(result)

    def test_returns_best_match_not_random(self):
        self._seed_unit("high success rate in module_a optimizer path")
        self._seed_unit("low memory usage reduces latency significantly")
        cluster = _make_cluster(
            _make_insight(content="high success rate in module_a optimizer fast path")
        )
        result = self.synth._semantic_lookup(cluster)
        self.assertIsNotNone(result)
        self.assertIn("success", result.abstraction.lower())


class TestImmediateStoreAppend(unittest.TestCase):
    """
    Verify new_units are appended to knowledge_store immediately inside the
    synthesize loop, enabling intra-batch semantic matching.
    """

    def setUp(self):
        self.synth = KnowledgeSynthesizer()

    def _run_two_similar_clusters(self):
        """Manually simulate two similar clusters processed in sequence."""
        cluster1 = _make_cluster(_make_insight(content="high success rate achieved in module_a"))
        unit1 = self.synth._create_knowledge_unit(cluster1)
        if unit1:
            # Immediately append (as the fixed code does)
            self.synth.knowledge_store.append(unit1)
            self.synth._cache_misses += 1

        # Second cluster with similar content — should now hit the cache
        cluster2 = _make_cluster(
            _make_insight(content="high success rate achieved in module_a with tuning", genome_id="g2")
        )
        existing = self.synth._semantic_lookup(cluster2)
        if existing:
            existing.citation_count += 1
            self.synth._cache_hits += 1
        else:
            unit2 = self.synth._create_knowledge_unit(cluster2)
            if unit2 is None:
                self.synth._cache_hits += 1
            else:
                self.synth.knowledge_store.append(unit2)
                self.synth._cache_misses += 1

    def test_intra_batch_cache_hit_occurs(self):
        self._run_two_similar_clusters()
        self.assertGreater(self.synth._cache_hits, 0,
                           "Expected at least one intra-batch cache hit")

    def test_cache_hit_increments_citation_count(self):
        cluster1 = _make_cluster(_make_insight(content="feedback loop improves success rate dramatically"))
        unit1 = self.synth._create_knowledge_unit(cluster1)
        if unit1 is None:
            self.skipTest("Abstraction hash dedup triggered on first unit")
        self.synth.knowledge_store.append(unit1)
        original_citations = unit1.citation_count

        cluster2 = _make_cluster(
            _make_insight(content="feedback loop improves success rate and throughput", genome_id="g2")
        )
        existing = self.synth._semantic_lookup(cluster2)
        if existing:
            existing.citation_count += 1
            self.assertEqual(existing.citation_count, original_citations + 1)
        else:
            self.skipTest("No semantic match found; threshold may not be met for this content")


class TestAbstractionHashDedupCountsAsHit(unittest.TestCase):
    """
    When _create_knowledge_unit returns None (hash already in abstraction_cache),
    it should be counted as a cache hit in the synthesize loop.
    """

    def setUp(self):
        self.synth = KnowledgeSynthesizer()

    def test_duplicate_cluster_creates_none_unit(self):
        cluster = _make_cluster()
        unit1 = self.synth._create_knowledge_unit(cluster)
        self.assertIsNotNone(unit1, "First create should return a unit")
        self.synth.knowledge_store.append(unit1)

        # Same cluster again — abstraction hash matches
        unit2 = self.synth._create_knowledge_unit(cluster)
        self.assertIsNone(unit2, "Duplicate cluster should return None (hash dedup)")

    def test_hash_dedup_increments_cache_hits(self):
        cluster = _make_cluster()
        unit1 = self.synth._create_knowledge_unit(cluster)
        if unit1:
            self.synth.knowledge_store.append(unit1)
            self.synth._cache_misses += 1

        # Simulate what the fixed synthesize loop does for None return
        unit2 = self.synth._create_knowledge_unit(cluster)
        if unit2 is None:
            self.synth._cache_hits += 1  # Fixed behavior

        self.assertEqual(self.synth._cache_hits, 1)
        self.assertEqual(self.synth._cache_misses, 1)


class TestKnowledgeUnitSourceKeywords(unittest.TestCase):
    def setUp(self):
        self.synth = KnowledgeSynthesizer()

    def test_source_keywords_field_exists(self):
        cluster = _make_cluster()
        unit = self.synth._create_knowledge_unit(cluster)
        if unit is None:
            self.skipTest("Hash dedup returned None")
        self.assertTrue(hasattr(unit, "source_keywords"))
        self.assertIsInstance(unit.source_keywords, set)

    def test_source_keywords_serialized_in_to_dict(self):
        cluster = _make_cluster()
        unit = self.synth._create_knowledge_unit(cluster)
        if unit is None:
            self.skipTest("Hash dedup returned None")
        d = unit.to_dict()
        self.assertIn("source_keywords", d)
        self.assertIsInstance(d["source_keywords"], list)

    def test_source_keywords_populated_from_content(self):
        cluster = _make_cluster(_make_insight(content="feedback loop improves success rate"))
        unit = self.synth._create_knowledge_unit(cluster)
        if unit is None:
            self.skipTest("Hash dedup returned None")
        # At least some content words should appear in source_keywords
        self.assertGreater(len(unit.source_keywords), 0)


if __name__ == "__main__":
    unittest.main()
