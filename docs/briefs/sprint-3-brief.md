# Sprint 3 — Discovery Brief

*Author: Mary (Analyst, BMAD) | Date: 2026-03-25 | Issue: EVO-31*

---

## Current State Summary

EvoForge v0.1.0 has shipped two sprint cycles:

**Sprint 1:** Core MEC framework, genome/variation operators, fitness evaluation scaffolding
**Sprint 2:** TokenCache (30-50% fewer LLM calls), ContextCompressor, ModelRouter (16.4% cost savings)

The framework can run evolutionary optimization loops and produce benchmark scores. However, **every benchmark run is `simulation_mode: true`** — scores are synthetically generated, not grounded in real task evaluation. We have cost-optimized infrastructure but no validated improvement signal.

---

## Benchmark Baselines (13 iterations as of 2026-03-24)

| Metric | Current Value | Trend | Health |
|--------|--------------|-------|--------|
| overall_score | 59.9 / 100 | — | Neutral |
| task_completion_rate | 54.96% | +6.4% | Improving |
| reasoning_quality | 63.8 | **-4.4%** | DECLINING |
| self_improvement_rate | 7.59 | Noisy (5.1–13.3 range) | Unreliable |
| token_efficiency | 3,754 | +1,803 | Improving |
| speed | 2.28 tasks/min | +1.39 | Improving |

### Metric Gaps

- **Simulation-only data**: No real task battery exists. Scores cannot be trusted as evidence of genuine improvement.
- **reasoning_quality is declining** while `self_improvement_rate` shows positive — direct contradiction. Our improvement metric measures something decoupled from actual reasoning.
- **PASS/FAIL logic is broken**: iteration 9 (reasoning_quality=83.98) → FAIL; iteration 7 (83.64) → PASS. No consistent threshold.
- **No fitness memory**: Genome changes are not tracked against outcome history. The system may re-evaluate identical genomes repeatedly.
- **Single-score aggregation hides tradeoffs**: task_completion rising while reasoning_quality falls is a regression, not progress. A weighted average cannot detect this.

---

## Techniques Worth Exploring

### 1. Held-Out Validation Battery (DSPy)
*Khattab et al., arXiv:2310.03714, 2023*

Create 30 fixed test tasks with ground-truth answers. Every genome mutation is scored against this battery on ≥3 consecutive runs before acceptance. Replaces `simulation_mode: true` with real validation. DSPy uses this as "compilation" — a change is only committed if it improves held-out dev set performance.

**Why it matters for EvoForge:** Without a fixed battery, we cannot distinguish genuine improvement from benchmark drift. This is the foundational fix.

---

### 2. Persistent Fitness Ledger with Genome Hash (OPRO)
*Yang et al., arXiv:2309.03409, 2023*

Maintain `{genome_hash → {best_score, timestamp, parent_genome_hash, mutation_applied}}`. Before evaluating any genome, check the ledger — if previously evaluated, reuse the score. OPRO's insight: the optimizer needs full history to avoid cycling through known-bad solutions.

**Why it matters for EvoForge:** Prevents 40-60% redundant evaluations. Creates an auditable evolution tree. Pairs directly with existing TokenCache infrastructure.

---

### 3. Multi-Metric Pareto Dominance Selection (NSGA-II)
*Deb et al., IEEE Trans. Evolutionary Computation, 2002*

Replace `overall_score = weighted_average(metrics)` with Pareto dominance: a genome G' is accepted only if it improves ≥1 metric without degrading any other. Objectives: {task_completion_rate, reasoning_quality, token_efficiency}.

**Why it matters for EvoForge:** Directly fixes the reasoning_quality regression. A mutation that raises task_completion but lowers reasoning_quality would be rejected, not averaged away.

---

### 4. Textual Gradient Attribution (TextGrad)
*Yuksekgonul et al., arXiv:2406.07496, 2024*

After each mutation, generate: `{mutation_type, before_score, after_score, attribution_text}`. The attribution text causally explains the delta. Incoherent attributions flag spurious improvements.

**Why it matters for EvoForge:** Creates auditable, human-readable evolution logs. Enables debugging of *why* the framework improves or regresses.

---

### 5. Control Population / Frozen Baseline
*Standard evolutionary computation (Holland 1992; applied in NAS: Real et al., AAAI 2019)*

Reserve 2-3 genomes per generation as zero-mutation controls. If `mean(evolved) - mean(control) < threshold` for 5+ generations, raise `EvolutionStalledWarning` and inject operator diversity.

**Why it matters for EvoForge:** Provides the scientific control group our benchmarks lack. Without a frozen baseline, we cannot prove the mutations — rather than random variation — are driving any improvement.

---

## Competitive Landscape

| Framework | Improvement Signal | Verified? |
|-----------|-------------------|-----------|
| DSPy | Held-out dev set, compiled teleprompter | Yes — statistically valid |
| TextGrad | Textual gradient + before/after metric | Yes — causally attributable |
| OPRO | Full score history in meta-prompt | Yes — anti-regressive by design |
| SEAgent | OS-World external benchmark | Yes — independent eval |
| **EvoForge** | **simulation_mode synthetic scores** | **No** |

EvoForge is behind every major framework in measurement rigor. Sprint 3 closes this gap.

---

## Recommended Sprint 3 Focus

### Priority 1 — Fitness Ledger (2 days)
`FitnessLedger` class in `evoforge/evolution/fitness_ledger.py`. Genome-hash keyed persistent store. Integrates with existing `TokenCache`. Eliminates redundant evaluations and creates evolution audit trail.

### Priority 2 — Fixed Validation Battery (1 day)
`tests/validation/battery.py` — 30 deterministic test tasks with ground-truth answers. Benchmark runner calls battery instead of simulation. Removes `simulation_mode: true` from all future runs.

### Priority 3 — Pareto Dominance Selection (2 days)
Refactor `evoforge/evolution/fitness.py` and `population.py`. Replace weighted-average selection with NSGA-II Pareto front. Objectives: task_completion_rate, reasoning_quality, token_efficiency. Fixes the reasoning_quality regression immediately.

**Defer to Sprint 4:** Textual Gradient Attribution (valuable but requires LLM call per mutation — adds latency until Fitness Ledger amortizes cost), Control Population (1 day, but needs Ledger first to be meaningful).

---

## Risks / Unknowns

1. **Validation battery construction**: Ground-truth answers require human curation or a trusted reference model. If tasks are too easy, the battery won't discriminate between genomes.
2. **Pareto front stability**: With only 5 metrics, Pareto fronts may be too large (many non-dominated solutions). May need objective reduction or crowding distance.
3. **FitnessLedger storage**: If genome space is large, ledger may grow unbounded. Need eviction policy (LRU or generation-based TTL).
4. **`simulation_mode` removal risk**: Removing simulation may expose that some genome operators produce errors in real eval. Expect initial FAIL rate to spike — this is expected and healthy.

---

## Lessons from Last Sprint (Ralph Loop)

> Sprint 2 optimized the *cost* of evolution (TokenCache, ModelRouter) without validating *whether* evolution is real. We made the loop faster and cheaper but didn't verify it's producing genuine improvement. The benchmark data confirms this: cost metrics (token_efficiency) are up, but quality metrics (reasoning_quality) are declining. Sprint 3 must establish measurement credibility before Sprint 4 optimizes further.

---

*Sprint 3 Discovery Brief — EvoForge AI — 2026-03-25*
