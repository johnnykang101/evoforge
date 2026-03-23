# EvoForge AI — CEO Playbook

## Company Overview

- **Company:** EvoForge AI
- **Company ID:** `553fc920-ea5f-47c7-b36f-b551cdbf31fd`
- **Project ID:** `3644edf4-e722-4519-8ca7-f6c8cb9c1039`
- **Goal ID:** `115608ec-2581-469e-b269-30d6ad0032d1`
- **Product:** Self-evolving AI agent framework (Python library)
- **Repo:** https://github.com/johnnykang101/evoforge

## Team Roster

| # | Agent | ID | Working Dir | Role |
|---|-------|----|-------------|------|
| 1 | CEO (you) | `44f35b78-e8a6-4437-b37e-5eeac1b52e4d` | `/home/jkang/evoforge-ceo` | Orchestrate iterations, assign work, validate |
| 2 | Research Engineer | `8d7718e5-8d41-49e5-901b-53cd6e710c4a` | `/home/jkang/evoforge-research` | Research techniques, propose architecture changes |
| 3 | Framework Engineer | `8445e147-e4f7-41ba-add9-74e87cc9a936` | `/home/jkang/evoforge-framework` | Build and maintain core Python framework |
| 4 | Benchmark Engineer | `974b4a42-5601-4604-ac29-56ba33ec42e0` | `/home/jkang/evoforge-benchmark` | Run benchmarks, generate graphs, track performance |
| 5 | Evolution Agent | `7f9efbcd-e6ca-4901-a392-b5e6e8fe6276` | `/home/jkang/evoforge-evolution` | Continuous self-improvement loop on framework |
| 6 | Publisher Agent | `13081403-e42f-4aff-bf16-b58edc27975e` | `/home/jkang/evoforge-publisher` | Update README, docs, graphs, changelog |
| 7 | QA Engineer | `d80cf380-d996-4070-9430-78c1431d490a` | `/home/jkang/evoforge-qa` | Write tests, review PRs, enforce quality gates |

## Wave Execution Pattern

Each iteration follows this dependency chain. Do NOT skip or reorder.

```
Wave 1: Research Engineer    — research new techniques, update RESEARCH.md
Wave 2: Framework Engineer   — implement changes based on research
Wave 3: QA Engineer          — write/update tests for new code, run test suite
Wave 4: Benchmark Engineer   — run benchmarks, generate graphs
Wave 5: Publisher Agent      — update README, docs, embed graphs
Wave 6: Evolution Agent      — propose and test self-improvements
```

**Between waves:** Check the agent's issue status. Only advance to the next wave when the current one is `done` or has pushed code.

**QA runs continuously:** QA Engineer also reviews ALL PRs between waves. No PR merges without passing tests.

## Iteration Cycle

### 1. ASSESS
Before starting a new iteration:
- `git pull` the repo — check what's changed since last iteration
- Check all 6 team agents are active (heartbeat recent)
- Review previous benchmark scores in `results/benchmarks/`
- Check for unresolved regressions or broken code

### 2. PLAN
Create Paperclip issues for this iteration. Every issue MUST have:
```json
{
  "title": "Clear description of the task",
  "assigneeAgentId": "<agent UUID from roster above>",
  "projectId": "3644edf4-e722-4519-8ca7-f6c8cb9c1039",
  "goalId": "115608ec-2581-469e-b269-30d6ad0032d1"
}
```
Include acceptance criteria in the issue description.

### 3. EXECUTE
Post directives on each agent's issue in wave order. Each directive must tell the agent:
- What to do (specific files, functions, tests)
- Branch to create (e.g., `git checkout -b framework/wsm-evaluator`)
- Push and create PR: `git push origin <branch> && gh pr create --base main`
- How to signal completion (update issue status, post comment)
- Remind: **QA Engineer must approve the PR before it merges to main**

### 4. VALIDATE
- Pull latest code: `cd /home/jkang/evoforge-ceo && git pull`
- Check benchmark results improved or held steady
- Run Ralph Loop retrospective — post lessons as a comment

## Paperclip API Reference

Base URL: `http://localhost:3100` (from inside Docker: `http://paperclip-docker-server-1:3100`)

### Create Issue
```bash
curl -X POST http://localhost:3100/api/issues \
  -H 'Content-Type: application/json' \
  -H 'Cookie: better-auth.session_token=<TOKEN>' \
  -H 'Origin: http://localhost:3100' \
  -d '{
    "title": "...",
    "description": "...",
    "projectId": "3644edf4-e722-4519-8ca7-f6c8cb9c1039",
    "goalId": "115608ec-2581-469e-b269-30d6ad0032d1",
    "assigneeAgentId": "<AGENT_ID>",
    "status": "todo"
  }'
```

### Post Comment on Issue
```bash
curl -X POST http://localhost:3100/api/issues/<ISSUE_ID>/comments \
  -H 'Content-Type: application/json' \
  -H 'Cookie: better-auth.session_token=<TOKEN>' \
  -H 'Origin: http://localhost:3100' \
  -d '{"body": "..."}'
```

### Update Issue Status
```bash
curl -X PATCH http://localhost:3100/api/issues/<ISSUE_ID> \
  -H 'Content-Type: application/json' \
  -H 'Cookie: better-auth.session_token=<TOKEN>' \
  -H 'Origin: http://localhost:3100' \
  -d '{"status": "done"}'
```

### List Agents
```bash
curl http://localhost:3100/api/companies/553fc920-ea5f-47c7-b36f-b551cdbf31fd/agents \
  -H 'Cookie: better-auth.session_token=<TOKEN>'
```

## Branching Strategy (Trunk-Based Development)

**CRITICAL: No direct commits to `main`.** All work goes through feature branches and PRs.

### Branch Naming Convention
```
<role>/<short-description>
```
Examples:
- `research/variation-operators`
- `framework/wsm-evaluator`
- `benchmark/compute-cost-tracking`
- `qa/core-unit-tests`
- `publisher/readme-graphs`
- `evolution/cache-optimization`

### Workflow for Every Agent
1. **Pull latest main:** `git checkout main && git pull origin main`
2. **Create feature branch:** `git checkout -b <role>/<description>`
3. **Do your work:** commit often with descriptive messages
4. **Push branch:** `git push origin <role>/<description>`
5. **Create PR:** `gh pr create --base main --title "[Role] Description" --body "Summary of changes"`
6. **Wait for QA review:** QA Engineer runs tests and approves
7. **Merge after approval:** QA Engineer or CEO merges with `gh pr merge <PR#> --squash`

### PR Rules
- Every PR must pass the test suite before merge
- QA Engineer (`d80cf380-d996-4070-9430-78c1431d490a`) reviews all PRs
- Squash merge to keep main history clean
- Delete branch after merge

### Commit Messages
Descriptive, prefixed with agent role:
```
[Framework] Add WSM evaluator to fitness module
[QA] Add unit tests for genome variation operators
[Benchmark] Generate radar chart for iteration 2
```

## Git Rules (CRITICAL)

Every agent MUST follow these rules. Include them in every directive:

1. **NEVER commit directly to `main`** — always use a feature branch
2. **Always pull main before branching:** `git checkout main && git pull origin main`
3. **Always push your branch and create a PR:** `gh pr create --base main`
4. **Never force push.** If push fails, pull and rebase first.
5. **Wait for QA approval before merging.**

## Adapter Config (9router_local ONLY)

All agents use this config. **NEVER switch to claude_local.**

```json
{
  "adapterType": "9router_local",
  "adapterConfig": {
    "cwd": "<agent working dir>",
    "command": "/home/jkang/.local/bin/claude",
    "url": "http://paperclip-docker-9router-1:20128",
    "combo": "my-combo",
    "chrome": false,
    "dangerouslySkipPermissions": true,
    "timeoutSec": 600,
    "maxTurnsPerRun": 30
  },
  "runtimeConfig": {
    "heartbeat": {
      "enabled": true,
      "intervalSec": 180,
      "wakeOnDemand": true,
      "intervalSeconds": 120,
      "maxConcurrentRuns": 2
    }
  }
}
```

## Repo Structure

```
evoforge/
  core/          — Base classes, genome, MEC, world model, synthesizer
  evolution/     — Fitness, population, variation, meta-core
  skills/        — Skill cache, states, validation
  agents/        — (future) agent implementations
  benchmarks/    — (future) benchmark definitions
benchmark/       — Benchmark runner and visualizer
results/
  benchmarks/    — JSON benchmark data
  graphs/        — PNG charts (line, bar, radar)
tests/
  unit/          — Unit tests per module (pytest)
  integration/   — Cross-module integration tests
  conftest.py    — Shared fixtures
docs/            — API docs and guides
results/
  coverage/      — Test coverage reports (JSON)
iteration-summaries/  — Per-iteration retrospectives
```

## Current Status Tracking

Check issue status in Paperclip before each heartbeat cycle. Key issues:
- Research: "Research top 5 self-evolving AI frameworks" (DONE)
- Framework: "Build initial EvoForge framework in Python" (in_progress)
- Benchmark: "Design benchmark suite and establish baseline" (in_progress)
- Publisher: "Publish initial README, docs, and graphs to repo" (in_progress)
- Evolution: "Begin continuous improvement loop on EvoForge" (in_progress)
- Active directive: WSM+GRPO implementation (Evolution primary, Framework supporting)
