# EvoForge Architecture: Self-Evolving AI Agent Framework

## Vision Statement

EvoForge is a meta-morphic AI agent framework that continuously evolves its own architecture through operational experience, transcending traditional static agent designs. Unlike frameworks that simply learn new skills or improve existing ones, EvoForge autonomously redesigns its internal components—selection algorithms, memory hierarchies, and planning strategies—to optimize for emerging environmental demands.

**Core Thesis**: An agent's architecture should not be a fixed blueprint but an evolvable phenotype, shaped by iterative variation, selection, and retention of successful configurations.

---

## Unique Architectural Pillars

### 1. Meta-Evolutionary Core (MEC)

The **Meta-Evolutionary Core** is EvoForge's innovation: a separate agent layer dedicated to evolving the agent framework itself.

**Components:**
- **Architecture Genome**: Encodes the agent's configuration as an evolvable genotype
  - Planning algorithm (e.g., ReAct, Chain-of-Thought, Tree-of-Thoughts)
  - Memory management strategy (vector DB, graph, episodic)
  - Tool selection policy and abstraction layer
  - Learning rate and optimization hyperparameters
  - Self-monitoring and evaluation frequency

- **Variation Operators**: Introduce architectural mutations
  - Crossover between successful agent configurations
  - Structural mutations (add/remove/replace components)
  - Parameter mutations with adaptive step sizes
  - Topology changes (connectivity between modules)

- **Fitness Evaluator**: Assesses architectural changes quantitatively
  - Multi-objective: task success rate, sample efficiency, compute cost, interpretability
  - Rolling baselines prevent regression
  - Automated A/B testing in parallel sandbox environments

**How It Differs**: Existing frameworks evolve skills or policies within a fixed architecture. MEC evolves the architecture itself—the principles that generate skills and policies.

---

### 2. Convergent Knowledge Synthesis Engine (CKSE)

Inspired by HealthFlow's ExperienceManager and SEAgent's World State Model, CKSE performs **explicit knowledge distillation across evolution cycles**.

**Pipeline:**

```
Execution → Raw Trajectories
    ↓
World Model → State Abstraction (What actually happened?)
    ↓
Reader → Causal & Procedural Extraction (Why did it work/fail?)
    ↓
Synthesis → Composite Knowledge Units (Cross-architectural insights)
    ↓
Re-encoding → Genome Annotation (Tunable architecture parameters)
```

**Key Innovations:**
- **Cross-Architecture Generalization**: Knowledge extracted from a "ReAct" architecture can inform improvements in a "Tree-of-Thoughts" agent
- **Causal Trace Reconstruction**: Uses a dedicated LLM to infer causal relationships between architectural changes and outcomes
- **Knowledge-Directed Mutation**: Architectural mutations are guided by synthesized knowledge, not random variation

**Novelty**: Most frameworks learn within-architectures. CKSE learns *about* architectures, enabling genuine metaevolution.

---

### 3. Skill Crystallization Cache with Chaîne of Validation

EvoForge implements an advanced skill lifecycle inspired by Moltron's crystallization but with formal guarantees.

**Skill States:**
1. **Prototype** (0-5 executions): Casual logs only
2. **Candidate** (5-50 executions): Basic telemetry, sandbox testing required
3. **Crystallized** (50+ executions): Immutable, versioned, production-certified
4. **Archived** (retired): Read-only access, triggers deprecation warnings

**Validation Pipeline (Chaîne):**
```
Pull Request → Unit Tests → Integration Tests → A/B Shadow Mode
    → Canary Rollout → Performance Regression Detection → Promoted
```

**Evolutionary Retention**: Even discarded skills are retained in "dead code museum" for possible resurrection through genome crossover.

---

### 4. Divergent Task Curriculum Generator

Borrowing from SEAgent's curriculum learner, but with explicit **evolutionary objectives**.

**Curriculum Loop:**
1. **Gap Analysis**: Identify tasks where current architecture underperforms
   - Compare fitness function component deviations
   - Detect performance plateaus across skill categories
2. **Probe Generation**: Create edge cases specifically targeting identified gaps
   - Use LLM to generate tasks that would stress weak architectural components
3. **Progressive Reveal**: Deploy new tasks only when a threshold of skill is reached
   - Prevents catastrophic forgetting during curriculum progression
4. **Founder Effect Mitigation**: Ensure enough task diversity to avoid local optima

**Unique Aspect**: The curriculum exists *to evolve the agent*, not to teach it specific skills. Tasks are chosen based on their potential to generate informative architectural mutations.

---

### 5. Federated Knowledge Pool (Optional Distributed Mode)

Enables multiple EvoForge instances to contribute to and learn from a shared knowledge pool without exposing sensitive data.

**Privacy-Preserving Architecture:**
- Each instance shares **abstracted knowledge units**, not raw trajectories
- Differential privacy noise added to cross-instance contributions
- Reputation-weighted voting in consensus mechanisms
- Knowledge provenance tracked via cryptographic signatures

**Use Cases**:
- Consortium-based evolution where organizations mutually benefit without sharing proprietary data
- Open-source "commons" of evolved architectures published by the community

---

## Data Flow & Component Interactions

```mermaid
graph TD
    A[User Goal] --> B{Task Router}
    B --> C[Active Architecture Instance]

    subgraph "Evolutionary Loop"
        C --> D[Execution Trace Collector]
        D --> E[World Model Abstractor]
        E --> F[Causal Reader]
        F --> G[Knowledge Synthesis]
        G --> H[Knowledge Store]
    end

    subgraph "Meta-Evolutionary Core"
        H --> I[Fitness Evaluator]
        I --> J[Genome Repository]
        J --> K[Variation Operators]
        K --> L[Child Architectures]
        L --> M[A/B Testing Sandbox]
        M --> N[Winnowing Selection]
        N --> J
    end

    N --> O[Promoted Architecture]
    O --> C

    subgraph "Skill System"
        C --> P[Skill Execution]
        P --> Q[Skill Telemetry]
        Q --> R[Validation Pipeline]
        R --> S[Skill Cache]
    end

    S --> P
    G --> T[Skill Design Advisor]
    T --> P
```

**Data Invarants:**
- **Traceability**: Every architectural decision links back to specific execution evidence
- **Reversibility**: Architecture rollbacks permitted using genome history
- **Safety**: Mutations evaluated in isolated sandbox before production deployment
- **Knowledge Conservation**: No insight discarded; poorly-performing architectures contribute to training data

---

## Evolutionary Strategy Design

### Selection Mechanism

**Multi-Tournament Selection with Diversity Bonus:**

```
population = active_architectures
selected = []

for tournament in parallel_tournaments:
    contestants = sample_with_diversity_bonus(population, k=8)
    winner = argmax_{c in contestants} (fitness(c) + λ * novelty(c))
    selected.append(winner)
```

- **Fitness**: Weighted sum of success rate, efficiency, interpretability scores
- **Novelty**: Distance to nearest neighbor in architectural feature space
- **λ**: Tunable diversity pressure (default 0.3; can evolve itself)

### Crossover Operator

**Modular Crossover with Constraint Propagation:**

```
parent_A, parent_B = selected_architectures()
child = initialize_from(parent_A)

for module in ALL_MODULES:
    if random() < crossover_rate:
        child[module] = parent_B[module]  # Swap entire modules
        propagate_constraints(child)  # Ensure compatibility
    else:
        child[module] = mutate_parameters(parent_A[module])
```

Constraints ensure, e.g., that selecting a high-throughput memory module pairs with compatible retrieval algorithms.

### Mutation Operators

1. **Parameter Mutation**: Gaussian noise on continuous parameters
2. **Structural Mutation**: Add/remove/replace modules; then re-validate constraints
3. **Topological Mutation**: Rewire inter-module connections
4. **Hypermutation**: Temporary increase in mutation rate when fitness plateaus

---

## Evolution Loop Timing & Phasing

### Phase 1: Exploration (Generations 0–100)
- High mutation rates (0.2–0.5 per genome)
- Small population (16–32 architectures)
- Intensive logging; fitness approx based on synthetic curriculum
- **Goal**: Discover viable architectural regions

### Phase 2: Intensification (Generations 101–500)
- Lower mutation (0.05–0.1), higher crossover
- Larger population (64–128)
- Fitness based on real User Goals (shadow mode only)
- Introduce **niche specialization**: Some architectures target specific goal types
- **Goal**: Refine promising architectures

### Phase 3: Exploitation (Generation 501+)
- Very low mutation (0.01)
- Focus on architecture **ensembles**: Multiple specialized agents voting
- Deploy top architectures to production with canary releases
- Fitness from actual user objectives with automated monitoring
- **Goal**: Optimize for real-world deployment

---

## Novelty Claim: Why EvoForge Is Different

| Aspect | Existing Frameworks | EvoForge |
|--------|---------------------|----------|
| Evolutionary Target | Skills, policies, or plans within fixed architecture | **Architecture itself** (the "genome" of the agent) |
| Knowledge Granularity | Trajectory- or task-specific | **Cross-architectural abstractions** that generalize |
| Selection Mechanism | Reinforcement signals on actions | **Multi-objective fitness on entire agent design** |
| Deployment | Single agent per framework | **Population of heterogeneous agents**, potentially dynamic |
| Meta-Capability | No evolution of evolution mechanism | **Explicit meta-evolution**: evolution parameters are evolved |

**Bottom Line**: EvoForge is not just another self-improving agent—it's a **self-redesigning agent framework** that treats architecture as the evolving unit, not just behavior.

---

## Implementation Roadmap (High-Level)

1. **Genome Representation**: Protobuf/JSON schema for modular agent architecture
2. **Base Architecture Library**: Implement 5–10 baseline modules (planners, memories, selectors)
3. **Variation & Constraint Engine**: With modular compatibility guarantees
4. **World Model**: Abstractor that converts raw traces into comparable state representations
5. **Fitness Function Suite**: Initially based on synthetic benchmarks, later real-world signals
6. **A/B Testing Sandbox**: Isolated execution environments with resource quotas
7. **Genome Repository + Versioning**: Audit trail of all evolutionary steps
8. **Dashboard**: Visualize evolution, inspect knowledge units, manually guide mutations

---

## Evaluation Criteria for Success

After 500 architecture generations (or ~100K task executions), EvoForge should demonstrate:

1. **Rate of Architectural Innovation**: Novel configurations not present in seed population exceed 40% of population
2. **Cross-Task Generalization**: Top architectures score within 15% of task-specific best on held-out task families
3. **Evolution Speed**: Per-generation improvement in aggregate population fitness > 2% over rolling 50-gen window
4. **Knowledge Reuse**: >60% of synthesized knowledge units cited in multiple architectural lineages
5. **Human Interpretability**: At least 3 high-fitness architectures that domain experts can understand and manually replicate

---

## Open Questions & Research Directions

1. **Credit Assignment at Architectural Level**: Which architectural change caused which outcome? Requires advanced causal inference.
2. **Catastrophic Forgetting Mitigation**: How to preserve valuable architecture features across aggressive mutations? Solution: "architectural immune system" that protects high-fitness modules.
3. **Evolutionary Stasis Detection**: When does further variation yield diminishing returns? Early stopping triggers need development.
4. **Safety & Alignment**: How to ensure evolved architectures remain aligned with human values? Requires value alignment fitness constraints.
5. **Scalability**: Population-based architecture evolution is computationally expensive. Hierarchical evolution (evolve modules separately) may be necessary for large frameworks.

---

## Sprint 3 — Making Self-Improvement Measurable

> **Sprint 3 Theme**: All 13 benchmark iterations are `simulation_mode: true`. No metric is trustworthy until evaluation is grounded in real tasks. Sprint 3 makes improvement *verifiable* before Sprint 4 makes it *faster*.

### Context: What Sprint 2 Delivered

Sprint 2 shipped three infrastructure components (all additive, no breaking changes):
- **TokenCache** (`evoforge/core/token_cache.py`): Content-addressable LRU cache — 30–50% fewer redundant LLM calls
- **ContextCompressor** (`evoforge/core/context_compression.py`): Reduces context window usage
- **ModelRouter** (`evoforge/core/model_router.py`): Cost-aware routing → 16.4% cost savings

**Sprint 2 Lesson (Ralph Loop)**: We optimized the evolution loop's cost without verifying its correctness. `reasoning_quality` declined -4.4% while `self_improvement_rate` showed positive — a direct contradiction revealing metric decoupling. Sprint 3 fixes the measurement layer first.

### Critical Gaps Addressed

| Gap | Evidence | Sprint 3 Fix |
|-----|----------|--------------|
| All scores are synthetic | 13/13 iterations: `simulation_mode: true` | ValidationBattery (real tasks) |
| No mutation memory | Genome re-evaluated even if previously tested | FitnessLedger |
| Metric gaming | `task_completion` ↑ while `reasoning_quality` ↓, both "pass" | ParetoSelection |
| Inconsistent thresholds | iter 9 (83.98) → FAIL; iter 7 (83.64) → PASS | Fixed battery + dominance selection |

---

### Component 1: FitnessLedger

**Purpose**: Persistent genome outcome history — prevents redundant evaluation and creates an auditable evolution tree.

**File**: `evoforge/core/fitness_ledger.py` *(new)*

**Data Model**:
```python
FitnessLedger:
    store: Dict[genome_hash, LedgerEntry]

LedgerEntry:
    genome_hash: str          # SHA-256 of json.dumps(genome.config, sort_keys=True)
    best_score: float         # Best scalar score ever observed for this genome
    pareto_metrics: dict      # {task_completion_rate, reasoning_quality, token_efficiency}
    timestamp: datetime
    parent_genome_hash: str   # Lineage tracing
    mutation_applied: str     # e.g. "crossover", "param_mutation:planning.algorithm"
    evaluation_count: int     # Times this genome has been evaluated
```

**Integration Points**:

```
FitnessEvaluator.evaluate_genome(genome)           [fitness.py]
    │
    ├─► FitnessLedger.lookup(genome_hash)
    │       hit  → return cached LedgerEntry (skip evaluation)
    │       miss → run ValidationBattery
    │                   │
    │                   └─► FitnessLedger.record(genome_hash, metrics)
    │
    └─► TokenCache.get/put (genome_hash as cache key)
            Pairs naturally — both keyed on content hash
```

**Key Interface**:
```python
class FitnessLedger:
    def lookup(self, genome_hash: str) -> Optional[LedgerEntry]
    def record(self, genome_hash: str, metrics: ParetoMetrics, mutation: str) -> None
    def get_lineage(self, genome_hash: str) -> List[LedgerEntry]  # evolution tree walk
    def save(self, path: str) -> None   # JSON serialization
    def load(self, path: str) -> None
```

**Genome Hashing** (no new code in `genome.py` needed):
```python
import hashlib, json
def genome_hash(genome: ArchitectureGenome) -> str:
    canonical = json.dumps(genome.config, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

**No breaking changes**: `FitnessEvaluator.evaluate_genome()` gains a `ledger: Optional[FitnessLedger]` parameter (default `None`). When `None`, behavior is identical to today.

**Expected ROI**: 40–60% reduction in redundant genome evaluations based on OPRO findings.

---

### Component 2: ValidationBattery

**Purpose**: Replace `simulation_mode: true` heuristics with 30 deterministic test tasks that have known correct answers. A mutation is only accepted if it improves battery score over 3 consecutive runs.

**File**: `evoforge/core/validation_battery.py` *(new)*

**Task Categories** (10 tasks each, 30 total):
| Category | Example Tasks | Correctness Signal |
|----------|--------------|-------------------|
| Math reasoning | Multi-step arithmetic, unit conversions | Exact numeric match |
| Code generation | Sort algorithm, string manipulation | Unit test pass/fail |
| Logical deduction | Syllogisms, constraint satisfaction | Boolean ground truth |

**Data Model**:
```python
ValidationTask:
    task_id: str
    category: str          # "math" | "code" | "logic"
    prompt: str
    ground_truth: str
    evaluator: Callable[[str], bool]   # deterministic checker

ValidationResult:
    task_id: str
    passed: bool
    latency_ms: float
    tokens_used: int

BatteryResult:
    task_completion_rate: float    # passed / total
    reasoning_quality: float       # weighted by category difficulty
    token_efficiency: float        # 1.0 / avg_tokens_per_task (normalized)
    raw_results: List[ValidationResult]
```

**Integration into Evolution Loop**:

```
meta_core.py: _evaluate_population(task_suite)
    │
    └─► for each genome:
            battery = ValidationBattery.load("evoforge/data/battery_v1.json")
            result  = battery.run(genome)           # real execution
            metrics = result.to_pareto_metrics()    # → ParetoMetrics
            ledger.record(genome_hash, metrics)
```

**Acceptance Gate** (replaces `_simulate_*` heuristics in `fitness.py`):
```python
# Old (simulation):
metrics = FitnessMetrics(
    task_success_rate=self._simulate_success_rate(genome),  # REMOVE
    ...
)

# New (real):
result = self.battery.run(genome)
metrics = result.to_pareto_metrics()  # feeds ParetoSelection directly
```

**File locations**:
- Battery definition: `evoforge/data/battery_v1.json` *(new)*
- Battery runner: `evoforge/core/validation_battery.py` *(new)*
- Acceptance logic: modify `evoforge/evolution/fitness.py` — replace `_simulate_*` methods

**No breaking changes**: `FitnessEvaluator.__init__()` gains `battery: Optional[ValidationBattery] = None`. When `None`, falls back to existing simulation (backward compatible during transition).

---

### Component 3: ParetoSelection (NSGA-II)

**Purpose**: Replace `overall_score = weighted_average(metrics)` with Pareto dominance selection. A mutation that raises `task_completion` while lowering `reasoning_quality` is **rejected**, not accepted.

**Files modified**:
- `evoforge/evolution/fitness.py` — add `ParetoMetrics`, dominance predicate
- `evoforge/evolution/population.py` — replace scalar sort with Pareto front computation

**Pareto Objectives** (Sprint 3):
```python
@dataclass
class ParetoMetrics:
    task_completion_rate: float   # 0.0–1.0  (maximize)
    reasoning_quality: float      # 0.0–1.0  (maximize)
    token_efficiency: float       # 0.0–1.0  (maximize, = 1/normalized_tokens)
```

**Dominance Predicate**:
```python
def dominates(a: ParetoMetrics, b: ParetoMetrics) -> bool:
    """Return True if genome A Pareto-dominates genome B."""
    objectives = ['task_completion_rate', 'reasoning_quality', 'token_efficiency']
    at_least_as_good = all(getattr(a, o) >= getattr(b, o) for o in objectives)
    strictly_better  = any(getattr(a, o) >  getattr(b, o) for o in objectives)
    return at_least_as_good and strictly_better
```

**Pareto Front Computation** (replaces scalar sort in `population.py`):
```python
def compute_pareto_front(genomes: List[ArchitectureGenome]) -> List[ArchitectureGenome]:
    """Return non-dominated set (Pareto front rank 0)."""
    front = []
    for candidate in genomes:
        dominated = False
        for other in genomes:
            if other is not candidate and dominates(other.pareto_metrics, candidate.pareto_metrics):
                dominated = True
                break
        if not dominated:
            front.append(candidate)
    return front
```

**Updated Evolution Loop** (in `meta_core.py` — additive change to `_evaluate_population`):

```
Old flow:
    fitness_scores: List[float] → sorted → top-N selected

New flow:
    pareto_metrics: List[ParetoMetrics] → pareto_front computed
        → front members are elites (always survive)
        → remaining slots filled by crowding distance (NSGA-II tiebreak)
        → scalar fitness score retained for logging/compatibility
```

**Integration with FitnessLedger**:

```
ValidationBattery.run(genome) → BatteryResult
    → BatteryResult.to_pareto_metrics() → ParetoMetrics
    → FitnessLedger.record(genome_hash, pareto_metrics)
    → Population.update_pareto(genome_idx, pareto_metrics)
    → ParetoSelection.compute_pareto_front(population)
```

**Backward compatibility**: `FitnessWeights` scalar scoring is retained. `genome.fitness` is still set (for logging, checkpointing, CKSE) as `mean(pareto_metrics objectives)`. Only the *selection* step changes from scalar sort to dominance check.

---

### Data Flow: Sprint 3 Full Picture

```
meta_core._evaluate_population()
    │
    ├─► for each genome in population:
    │       hash = genome_hash(genome)
    │       │
    │       ├─ FitnessLedger.lookup(hash)
    │       │       HIT  ──────────────────────────────────┐
    │       │       MISS → ValidationBattery.run(genome)   │
    │       │                   → BatteryResult            │
    │       │                   → FitnessLedger.record()   │
    │       │                                              │
    │       └─► ParetoMetrics ←────────────────────────────┘
    │
    └─► Population.update_pareto(genome_idx, pareto_metrics)

meta_core.evolve() — after evaluation:
    │
    ├─► pareto_front = ParetoSelection.compute_pareto_front(population)
    ├─► crowding_sort(remaining)         # NSGA-II rank 1, 2, ...
    └─► VariationEngine.create_next_generation(pareto_front + ranked_rest)
```

---

### File / Module Summary for Framework Engineer

| File | Action | Purpose |
|------|--------|---------|
| `evoforge/core/fitness_ledger.py` | **CREATE** | FitnessLedger class + LedgerEntry dataclass |
| `evoforge/core/validation_battery.py` | **CREATE** | ValidationBattery runner + ValidationTask/Result |
| `evoforge/data/battery_v1.json` | **CREATE** | 30 deterministic test tasks (math/code/logic) |
| `evoforge/evolution/fitness.py` | **MODIFY** | Add ParetoMetrics; wire battery into evaluate_genome(); keep _simulate_* as fallback |
| `evoforge/evolution/population.py` | **MODIFY** | Add pareto_metrics field to genomes; add compute_pareto_front(); retain scalar fitness for compat |
| `evoforge/evolution/meta_core.py` | **MODIFY** | Pass ledger + battery to _evaluate_population(); call ParetoSelection after evaluation |

**No files deleted. No existing public interfaces changed. All modifications are additive.**

---

### Implementation Readiness Assessment

**Ready to implement** (no blockers):
- `ArchitectureGenome.config` is a plain dict — SHA-256 hashing is trivial
- `FitnessEvaluator.evaluate_genome()` already accepts optional params — ledger wires cleanly
- `Population.update_fitness()` has clear update path — `update_pareto()` mirrors it
- `_evaluate_population()` in `meta_core.py` is a clean loop — battery substitution is local

**Risk flags**:
1. **ValidationBattery cold-start**: 30 tasks must be authored before any real scores exist. Mitigation: keep `_simulate_*` fallback until battery JSON is populated.
2. **Pareto front collapse**: If all genomes are non-dominated (common early in evolution), crowding distance must break ties. Implement NSGA-II crowding distance in Sprint 3 to avoid neutral drift.
3. **FitnessLedger persistence path**: Ledger must survive process restarts. Use `EvolutionConfig.ledger_path` and call `ledger.save()` in `_save_checkpoint()`.
4. **Scalar fitness retained for CKSE**: `GenomeAnnotator` reads `genome.fitness` — keep scalar populated (as mean of Pareto objectives) to avoid breaking CKSE pipeline.

**Deferred to Sprint 4** (per Research Engineer recommendation):
- Textual Gradient Attribution Logging (TextGrad) — valuable but high LLM cost
- Control Population / Frozen Baseline — needs FitnessLedger first

---

### ADR Reference

See `docs/adr/ADR-003-pareto-selection.md` for decision record on replacing scalar fitness with Pareto dominance.

---

## Conclusion

EvoForge's architecture is itself an early prototype, expected to evolve significantly under its own evolutionary mechanisms. The ambition is not to build a perfect agent framework up-front, but to build a framework that can discover how to build perfect agent frameworks through sustained operation and experience.

**The ultimate test of EvoForge**: After running it for sufficient time, we should be able to examine the evolved architectures and find ideas we never would have thought of ourselves.


---

*EvoForge AI Framework - Architecture Draft v0.1*
*Based on research of state-of-the-art self-evolving frameworks (March 2026)*