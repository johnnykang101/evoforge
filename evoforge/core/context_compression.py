"""
EvoForge Core - Context Compression.
Reduces prompt sizes by compressing context before LLM calls.
Implements multiple strategies: deduplication, truncation, and summarization.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of a context compression operation."""
    original_tokens: int
    compressed_tokens: int
    strategy_used: str
    content: str

    @property
    def savings_ratio(self) -> float:
        """Fraction of tokens saved (0.0 = no savings, 1.0 = all removed)."""
        if self.original_tokens == 0:
            return 0.0
        return 1.0 - (self.compressed_tokens / self.original_tokens)


class ContextCompressor:
    """Compresses context/prompts to reduce token usage.

    Strategies (applied in order):
    1. Deduplication: Remove repeated sections within context
    2. Truncation: Keep only the most recent/relevant context within a budget
    3. Structural pruning: Strip verbose formatting, collapse whitespace

    Configurable via max_tokens budget and strategy weights.
    """

    def __init__(self, max_context_tokens: int = 4096,
                 dedup_enabled: bool = True,
                 pruning_enabled: bool = True):
        self.max_context_tokens = max_context_tokens
        self.dedup_enabled = dedup_enabled
        self.pruning_enabled = pruning_enabled
        self._total_original = 0
        self._total_compressed = 0

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (~4 chars per token heuristic)."""
        return max(1, len(text) // 4)

    def compress(self, context: str, strategy: str = "auto") -> CompressionResult:
        """Compress a context string.

        Args:
            context: Raw context/prompt text
            strategy: "auto", "dedup", "truncate", or "prune"

        Returns:
            CompressionResult with compressed content and metrics
        """
        original_tokens = self.estimate_tokens(context)
        result = context

        if strategy == "auto":
            # Apply all enabled strategies in sequence
            if self.dedup_enabled:
                result = self._deduplicate(result)
            if self.pruning_enabled:
                result = self._structural_prune(result)
            result = self._truncate(result, self.max_context_tokens)
            strategy_used = "auto"
        elif strategy == "dedup":
            result = self._deduplicate(result)
            strategy_used = "dedup"
        elif strategy == "truncate":
            result = self._truncate(result, self.max_context_tokens)
            strategy_used = "truncate"
        elif strategy == "prune":
            result = self._structural_prune(result)
            strategy_used = "prune"
        else:
            strategy_used = "none"

        compressed_tokens = self.estimate_tokens(result)
        self._total_original += original_tokens
        self._total_compressed += compressed_tokens

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            strategy_used=strategy_used,
            content=result
        )

    def _deduplicate(self, text: str) -> str:
        """Remove duplicate lines/paragraphs from context."""
        lines = text.split('\n')
        seen_hashes = set()
        unique_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                unique_lines.append(line)
                continue
            h = hashlib.md5(stripped.encode()).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_lines.append(line)

        return '\n'.join(unique_lines)

    def _structural_prune(self, text: str) -> str:
        """Remove verbose formatting and collapse whitespace."""
        lines = text.split('\n')
        pruned = []
        prev_empty = False

        for line in lines:
            # Collapse multiple consecutive empty lines
            stripped = line.strip()
            if not stripped:
                if not prev_empty:
                    pruned.append('')
                prev_empty = True
                continue
            prev_empty = False

            # Strip trailing whitespace
            pruned.append(line.rstrip())

        return '\n'.join(pruned)

    def _truncate(self, text: str, max_tokens: int) -> str:
        """Truncate context to fit within token budget.

        Keeps the end of the context (most recent/relevant) when truncating.
        """
        current_tokens = self.estimate_tokens(text)
        if current_tokens <= max_tokens:
            return text

        # Keep the last max_tokens worth of characters
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            truncated = text[-max_chars:]
            # Find first newline to avoid cutting mid-line
            first_newline = truncated.find('\n')
            if first_newline > 0 and first_newline < len(truncated) // 4:
                truncated = truncated[first_newline + 1:]
            return truncated

        return text

    def compress_trajectory(self, trajectory_states: List[Dict[str, Any]],
                            keep_last_n: int = 10) -> List[Dict[str, Any]]:
        """Compress a trajectory by keeping only the most informative states.

        Args:
            trajectory_states: List of state dicts from execution
            keep_last_n: Number of most recent states to always keep

        Returns:
            Compressed list of states
        """
        if len(trajectory_states) <= keep_last_n:
            return trajectory_states

        # Always keep first state (initial) and last N states
        compressed = [trajectory_states[0]]

        # Sample middle states at key transitions (success/error boundaries)
        middle = trajectory_states[1:-keep_last_n]
        for i, state in enumerate(middle):
            category = state.get('category', '')
            prev_category = middle[i - 1].get('category', '') if i > 0 else ''
            # Keep states at category transitions
            if category != prev_category:
                compressed.append(state)

        # Append the last N states
        compressed.extend(trajectory_states[-keep_last_n:])
        return compressed

    @property
    def stats(self) -> Dict[str, Any]:
        """Return compression performance statistics."""
        return {
            "total_original_tokens": self._total_original,
            "total_compressed_tokens": self._total_compressed,
            "total_savings": self._total_original - self._total_compressed,
            "savings_ratio": (1.0 - self._total_compressed / self._total_original)
            if self._total_original > 0 else 0.0,
        }
