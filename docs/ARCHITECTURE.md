# EvoForge — Architecture Document

> Maintained by: Evolution Agent (Architect)
> Updated each sprint in Phase 2 (ARCHITECT).

---

## System Overview

EvoForge is a self-evolving AI agent framework in Python. Agents run tasks, evaluate their own performance, propose improvements to their own code, test improvements, and merge successful ones — creating a continuous self-improvement loop.

## Core Components

```
evoforge/
  core/          — Base classes (Agent, Genome, WorldModel, Synthesizer)
  evolution/     — Fitness evaluation, population management, variation operators
  skills/        — Skill cache, skill states, validation
  agents/        — Concrete agent implementations
benchmark/       — Benchmark runner and visualizer
results/
  benchmarks/    — JSON data per sprint
  graphs/        — PNG charts embedded in README
tests/
  unit/          — Per-module unit tests
  integration/   — Cross-module tests
docs/
  PRD.md         — Sprint requirements (CEO)
  ARCHITECTURE.md — This file (Evolution Agent)
  adr/           — Architecture Decision Records
  briefs/        — Research discovery briefs
  stories/       — Sprint user stories
  benchmarks/    — Human-readable benchmark summaries
iteration-summaries/ — Sprint retrospectives (CEO)
```

## Self-Evolution Mechanism

1. Agent runs a task and records performance metrics
2. Fitness function evaluates the result
3. Variation operators propose mutations to agent genome
4. Mutations are tested against benchmark suite
5. Successful mutations (positive fitness delta) are merged
6. Unsuccessful mutations are discarded

## Current Architecture Decisions

*(Evolution Agent updates this section each sprint)*

---

## Sprint History

### Sprint 1 (initial)
- Established core genome + fitness architecture
- WSM evaluator added to fitness module

*(Evolution Agent adds new sprint section here each iteration)*
