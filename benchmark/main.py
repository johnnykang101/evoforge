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
from .visualizer import BenchmarkVisualizer


def main():
    """Execute complete benchmark pipeline."""
    print("=" * 60)
    print("EvoForge Benchmark Suite")
    print("=" * 60)

    # Step 1: Run benchmarks
    print("\n[1/3] Running benchmark suite...")
    runner = BenchmarkRunner()
    results = runner.generate_simulation_data(iterations=12)
    output_path = runner.save_results(results)
    print(f"      Results saved to: {output_path}")

    # Determine verdict
    if len(results) >= 2:
        verdict = runner.calculate_verdict(results[-1]["metrics"], results[-2]["metrics"])
        print(f"      Verdict vs previous: {verdict}")
    else:
        print("      Verdict: Baseline (first iteration)")

    # Step 2: Generate visualizations
    print("\n[2/3] Generating visualizations...")
    visualizer = BenchmarkVisualizer()
    graphs = visualizer.generate_all_visualizations()

    for name, path in graphs.items():
        print(f"      {name}: {path}")

    # Step 3: Summary
    print("\n[3/3] Summary")
    print(f"      Total iterations: {len(results)}")
    print(f"      Latest task completion: {results[-1]['metrics']['task_completion_rate']:.2%}")
    print(f"      Latest reasoning quality: {results[-1]['metrics']['reasoning_quality']:.1f}/100")

    print("\n" + "=" * 60)
    print("Benchmark suite complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
