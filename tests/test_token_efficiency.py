"""Tests for token efficiency features: TokenCache and ContextCompressor (EVO-9)."""
import pytest
from evoforge.core.token_cache import TokenCache
from evoforge.core.context_compression import ContextCompressor
from evoforge.evolution.meta_core import EvolutionConfig
from evoforge.evolution.fitness import FitnessWeights


# --- TokenCache ---

def test_token_cache_miss_on_empty():
    cache = TokenCache()
    assert cache.get("hello world") is None


def test_token_cache_hit_after_put():
    cache = TokenCache()
    cache.put("hello world", response="result", token_count=10)
    assert cache.get("hello world") == "result"


def test_token_cache_hit_rate_zero_on_empty():
    cache = TokenCache()
    assert cache.hit_rate == 0.0


def test_token_cache_hit_rate_after_hits():
    cache = TokenCache()
    cache.put("prompt", response="resp", token_count=5)
    cache.get("prompt")   # hit
    cache.get("other")    # miss
    assert cache.hit_rate == pytest.approx(0.5, rel=1e-3)


def test_token_cache_tokens_saved():
    cache = TokenCache()
    cache.put("prompt", response="resp", token_count=20)
    cache.get("prompt")   # hit — saves 20 tokens
    assert cache.tokens_saved == 20


def test_token_cache_clear():
    cache = TokenCache()
    cache.put("prompt", response="resp", token_count=5)
    cache.clear()
    assert cache.get("prompt") is None


def test_token_cache_model_key_separation():
    cache = TokenCache()
    cache.put("prompt", response="gpt4-result", token_count=10, model="gpt-4")
    cache.put("prompt", response="sonnet-result", token_count=8, model="claude-sonnet")
    assert cache.get("prompt", model="gpt-4") == "gpt4-result"
    assert cache.get("prompt", model="claude-sonnet") == "sonnet-result"


# --- ContextCompressor ---

def test_compressor_estimate_tokens():
    est = ContextCompressor.estimate_tokens("hello world")
    assert est > 0


def test_compressor_returns_compression_result():
    c = ContextCompressor()
    result = c.compress("short text")
    assert hasattr(result, "content")
    assert hasattr(result, "original_tokens")
    assert hasattr(result, "compressed_tokens")


def test_compressor_does_not_expand():
    c = ContextCompressor()
    text = "this is a simple short context"
    result = c.compress(text)
    assert result.compressed_tokens <= result.original_tokens + 5  # tolerance


def test_compressor_savings_ratio_range():
    c = ContextCompressor()
    result = c.compress("some text " * 50)
    assert 0.0 <= result.savings_ratio <= 1.0


def test_compressor_stats_keys():
    c = ContextCompressor()
    c.compress("a b c")
    stats = c.stats
    assert "total_original_tokens" in stats


# --- EvolutionConfig dataclass (regression guard) ---

def test_evolution_config_default_instantiation():
    """Regression: FitnessWeights mutable default must use field(default_factory=...)."""
    cfg1 = EvolutionConfig()
    cfg2 = EvolutionConfig()
    # Must be independent instances, not the same object
    assert cfg1.weights is not cfg2.weights


def test_evolution_config_custom_weights():
    w = FitnessWeights(task_success_rate=0.5, sample_efficiency=0.5,
                       compute_efficiency=0.0, interpretability=0.0, stability=0.0)
    cfg = EvolutionConfig(weights=w)
    assert cfg.weights.task_success_rate == pytest.approx(0.5)
