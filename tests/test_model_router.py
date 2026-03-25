"""Tests for model_router.py — compute cost optimization (EVO-10)."""
import pytest
from evoforge.core.model_router import ModelRouter, TaskComplexity, ModelTier, REFERENCE_COSTS


def test_simple_task_gets_simple_model():
    router = ModelRouter()
    decision = router.route("t1", "add two numbers", token_count=50)
    assert decision.complexity == TaskComplexity.SIMPLE


def test_complex_task_gets_complex_model():
    router = ModelRouter()
    decision = router.route("t2", "analyze and debug this multi-step reasoning chain", token_count=800)
    assert decision.complexity == TaskComplexity.COMPLEX


def test_moderate_task_routing():
    router = ModelRouter()
    decision = router.route("t3", "summarize this document", token_count=300)
    assert decision.complexity == TaskComplexity.MODERATE


def test_high_token_count_is_complex():
    router = ModelRouter()
    # "analyze" is a complex keyword; high token count confirms COMPLEX
    decision = router.route("t4", "analyze this large document", token_count=2000)
    assert decision.complexity == TaskComplexity.COMPLEX


def test_routing_decision_has_cost_fields():
    router = ModelRouter()
    decision = router.route("t5", "convert JSON to CSV", token_count=200)
    assert decision.actual_cost >= 0
    assert decision.baseline_cost >= 0
    assert decision.tokens_used == 200


def test_simple_task_cheaper_than_baseline():
    router = ModelRouter()
    decision = router.route("t6", "add 2 + 2", token_count=20)
    assert decision.actual_cost <= decision.baseline_cost


def test_cost_summary_after_routes():
    router = ModelRouter()
    router.route("t1", "add numbers", token_count=50)
    router.route("t2", "analyze complex architecture", token_count=1000)
    summary = router.get_cost_summary()
    assert summary["total_tasks"] == 2
    assert "total_actual_cost_usd" in summary
    assert "savings_pct" in summary


def test_cost_savings_positive_for_simple_tasks():
    router = ModelRouter()
    router.route("t1", "short simple task", token_count=100)
    summary = router.get_cost_summary()
    assert summary["total_actual_cost_usd"] >= 0
    assert summary["total_baseline_cost_usd"] >= summary["total_actual_cost_usd"]


def test_routing_distribution_tracks_all():
    router = ModelRouter()
    router.route("t1", "simple", 50)
    router.route("t2", "explain this concept", 300)
    router.route("t3", "analyze and debug complex chain", 900)
    summary = router.get_cost_summary()
    dist = summary.get("routing_distribution", {})
    total = sum(dist.values())
    assert total == 3


def test_reference_costs_ordered():
    # Simple should always be cheapest
    assert REFERENCE_COSTS[TaskComplexity.SIMPLE] <= REFERENCE_COSTS[TaskComplexity.MODERATE]
    assert REFERENCE_COSTS[TaskComplexity.MODERATE] <= REFERENCE_COSTS[TaskComplexity.COMPLEX]
