"""
EvoForge Core - Token Cache.
Caches LLM responses to avoid redundant API calls.
Uses content-addressable hashing for fast lookup.
"""

import hashlib
import json
import time
import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached LLM response with metadata."""
    response: Any
    token_count: int
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0


class TokenCache:
    """Content-addressable cache for LLM responses.

    Avoids redundant LLM calls by caching responses keyed on
    a hash of (prompt, model, parameters). Implements LRU eviction
    and TTL-based expiry.

    Typical savings: 30-50% fewer LLM calls on repeated evolution
    evaluations where similar prompts recur across generations.
    """

    def __init__(self, max_entries: int = 1024, ttl_seconds: float = 3600.0):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._tokens_saved = 0

    def _compute_key(self, prompt: str, model: str = "",
                     params: Optional[Dict[str, Any]] = None) -> str:
        """Compute content-addressable hash key."""
        key_data = {
            "prompt": prompt,
            "model": model,
            "params": params or {}
        }
        raw = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, model: str = "",
            params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Look up a cached response.

        Returns:
            Cached response if found and not expired, else None.
        """
        key = self._compute_key(prompt, model, params)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Check TTL
        if time.time() - entry.created_at > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        # LRU: move to end
        self._cache.move_to_end(key)
        entry.access_count += 1
        entry.last_accessed = time.time()
        self._hits += 1
        self._tokens_saved += entry.token_count
        logger.debug(f"Cache hit: saved {entry.token_count} tokens")
        return entry.response

    def put(self, prompt: str, response: Any, token_count: int,
            model: str = "", params: Optional[Dict[str, Any]] = None) -> None:
        """Store an LLM response in cache."""
        key = self._compute_key(prompt, model, params)

        # Evict if at capacity
        while len(self._cache) >= self.max_entries:
            self._cache.popitem(last=False)  # Remove oldest

        now = time.time()
        self._cache[key] = CacheEntry(
            response=response,
            token_count=token_count,
            created_at=now,
            access_count=0,
            last_accessed=now
        )

    def invalidate(self, prompt: str, model: str = "",
                   params: Optional[Dict[str, Any]] = None) -> bool:
        """Remove a specific entry. Returns True if found."""
        key = self._compute_key(prompt, model, params)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """Return cache performance statistics."""
        total = self._hits + self._misses
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "tokens_saved": self._tokens_saved,
        }

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def tokens_saved(self) -> int:
        return self._tokens_saved
