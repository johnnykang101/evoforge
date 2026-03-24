"""EvoForge Benchmark Suite - Main Entry Point.

Runs full benchmark pipeline:
1. Generate/collect metrics
2. Save JSON results
3. Create visualizations
4. Update README with graphs

Usage:
    python -m benchmark.main
"""

import sys
from pathlib import Path

from .runner import BenchmarkRunner


def main():
    """Execute complete benchmark pipeline."""
    print("=" * 60)
    print("EvoForge Benchmark Suite")
    print("=" * 60)

    # Run complete benchmark pipeline
    runner = BenchmarkRunner()
    results = runner.run()

    print("\n" + "=" * 60)
    print("Benchmark suite complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
