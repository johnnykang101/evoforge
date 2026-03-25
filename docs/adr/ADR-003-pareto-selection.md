# ADR-003: Replace Scalar Fitness with Pareto Dominance Selection

**Status**: Proposed
**Sprint**: 3
**Author**: Evolution Agent (Winston)
**Date**: 2026-03-25

---

## Context

Sprint 3 benchmark analysis revealed a critical flaw in the current fitness aggregation strategy:

- `reasoning_quality` declined **-4.4%** from baseline (68.22 → 63.8)
- `task_completion_rate` increased **+6.4%** over the same period
- Both iterations were scored as "improving" under `overall_score = weighted_average(metrics)`

This is metric decoupling: the weighted average allows one objective's gain to mask another's regression. The framework has no structural guarantee that accepting a mutation won't silently degrade any individual metric.

Additionally, PASS/FAIL verdicts are inconsistent:
- Iteration 9 (reasoning_quality=83.98) → FAIL
- Iteration 7 (reasoning_quality=83.64) → PASS

No coherent threshold logic exists under the current scalar approach.

## Decision

Replace scalar fitness sorting in `population.py` with **Pareto dominance selection** based on NSGA-II (Deb et al., 2002).

**Sprint 3 Pareto objectives:**
1. `task_completion_rate` (maximize)
2. `reasoning_quality` (maximize)
3. `token_efficiency` (maximize, defined as 1/normalized_tokens)

**Dominance rule**: Genome A dominates Genome B if A is at least as good as B on all objectives AND strictly better on at least one.

A mutation is only accepted into the population if it is Pareto-non-dominated — i.e., it does not degrade any objective while improving at least one.

## Alternatives Considered

### Option A: Re-tune Weighted Average
Adjust weights in `FitnessWeights` to penalize `reasoning_quality` regression more heavily.

**Rejected because**: Weights are arbitrary and require manual tuning each sprint. Does not solve the structural masking problem — a sufficiently large gain on one metric can still hide any regression.

### Option B: Hard Threshold Guards
Reject any mutation where any metric drops below a fixed floor (e.g., `reasoning_quality >= 60.0`).

**Rejected because**: Thresholds are brittle and require hand-tuning per benchmark baseline. Inconsistent threshold behavior was already observed (iterations 7 vs. 9). Does not leverage multi-objective structure.

### Option C: Pareto Dominance Selection (NSGA-II) ← CHOSEN
Structural guarantee: no accepted genome can be worse than its parent on any measured objective. Tiebreaking via crowding distance preserves population diversity. Scales naturally to more objectives in Sprint 4+.

## Consequences

**Positive:**
- Eliminates `reasoning_quality` regression by construction — a mutation that lowers it cannot dominate a genome that doesn't
- Removes need for hand-tuned threshold logic
- Pairs naturally with FitnessLedger — `ParetoMetrics` stored per genome hash
- Extensible: Sprint 4 can add `stability` or `interpretability` as objectives without architectural change

**Negative / Risks:**
- Pareto front collapse: early in evolution, all genomes may be mutually non-dominated. Mitigation: implement NSGA-II crowding distance for tiebreaking, which preserves diversity
- Framework Engineer must add `pareto_metrics` field to `ArchitectureGenome` — minor schema addition
- CKSE `GenomeAnnotator` reads `genome.fitness` (scalar). Mitigation: retain scalar as `mean(pareto_objectives)` — no CKSE changes needed

**Backward compatibility**: Scalar `genome.fitness` is retained for logging, checkpointing, and CKSE compatibility. Only the *selection step* in `population.evolve()` changes.

## Implementation Scope

| File | Change |
|------|--------|
| `evoforge/evolution/fitness.py` | Add `ParetoMetrics` dataclass; add `dominates()` predicate |
| `evoforge/evolution/population.py` | Add `compute_pareto_front()`; replace scalar sort in selection |
| `evoforge/evolution/meta_core.py` | Call `update_pareto()` after battery evaluation |

## References

- Deb, K. et al. "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II." *IEEE Transactions on Evolutionary Computation* 6(2), 2002.
- Research findings: `RESEARCH.md` — Sprint 3 Discovery section, "Multi-Metric Pareto Dominance Selection"
- EVO-33: BMAD Sprint 3 Architecture Phase
