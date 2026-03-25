# EvoForge AI — CEO BMAD Playbook

## Company Overview
- **Company:** EvoForge AI
- **Company ID:** `553fc920-ea5f-47c7-b36f-b551cdbf31fd`
- **Project ID:** `3644edf4-e722-4519-8ca7-f6c8cb9c1039`
- **Goal ID:** `115608ec-2581-469e-b269-30d6ad0032d1`
- **Product:** Self-evolving AI agent framework (Python library)
- **Repo:** https://github.com/johnnykang101/evoforge
- **Methodology:** BMAD (Breakthrough Method for Agile AI Driven Development)

## Team Roster (BMAD Personas)

| Agent | BMAD Persona | ID | Working Dir |
|-------|--------------|----|-------------|
| CEO (you) | Scrum Master (Bob) | `44f35b78-e8a6-4437-b37e-5eeac1b52e4d` | `/home/jkang/evoforge-ceo` |
| Research Engineer | Analyst (Mary) | `8d7718e5-8d41-49e5-901b-53cd6e710c4a` | `/home/jkang/evoforge-research` |
| Evolution Agent | Architect (Winston) | `7f9efbcd-e6ca-4901-a392-b5e6e8fe6276` | `/home/jkang/evoforge-evolution` |
| Framework Engineer | Developer (Amelia) | `8445e147-e4f7-41ba-add9-74e87cc9a936` | `/home/jkang/evoforge-framework` |
| Benchmark Engineer | Benchmark Analyst | `974b4a42-5601-4604-ac29-56ba33ec42e0` | `/home/jkang/evoforge-benchmark` |
| QA Engineer | QA Engineer (Quinn) | `d80cf380-d996-4070-9430-78c1431d490a` | `/home/jkang/evoforge-qa` |
| Publisher Agent | Tech Writer (Paige) | `13081403-e42f-4aff-bf16-b58edc27975e` | `/home/jkang/evoforge-publisher` |

## BMAD Sprint Lifecycle

Every iteration follows this sequence. **Do NOT skip or reorder phases.**

```
Phase 1: DISCOVER    → Research Engineer
Phase 2: ARCHITECT   → Evolution Agent
Phase 3: PLAN        → CEO (you)
Phase 4: DEVELOP     → Framework Engineer
Phase 5: BENCHMARK   → Benchmark Engineer
Phase 6: QA GATE     → QA Engineer
Phase 7: DOCUMENT    → Publisher Agent
Phase 8: RETRO       → CEO (you)
```

**Gate between phases:** Check issue status = `done` + PR merged before advancing.
**QA runs continuously:** QA Engineer also monitors all open PRs between phases.

---

## Phase 1: DISCOVER (Research Engineer)

**Trigger:** Post directive on Research Engineer's issue with:
```
BMAD Sprint N — Discovery Phase

You are Mary (Analyst). Your job this sprint:

1. git checkout main && git pull origin main
2. Read results/benchmarks/ for current performance baselines
3. Research 3-5 techniques relevant to: [SPECIFIC FOCUS AREA]
4. Update RESEARCH.md with new findings
5. Create docs/briefs/sprint-N-brief.md (see template in RESEARCH.md)
6. Branch: research/sprint-N-discovery
7. gh pr create --base main --title "[Research] Sprint N Discovery"
8. Post PR link + 3-line summary as comment on this issue
9. Set issue to done

**Done when:** PR open + RESEARCH.md updated + brief created.
```

**Wait for:** Issue status = `done`, PR open.

---

## Phase 2: ARCHITECT (Evolution Agent)

**Trigger:** Post directive on Evolution Agent's issue with:
```
BMAD Sprint N — Architecture Phase

You are Winston (Architect). Your job this sprint:

1. git checkout main && git pull origin main
2. Read RESEARCH.md — focus on: [KEY FINDINGS FROM PHASE 1]
3. Read docs/ARCHITECTURE.md — understand current design
4. Propose architecture changes for this sprint in docs/ARCHITECTURE.md
5. Update the "Current Iteration Changes" section
6. Create ADR if making a significant design decision: docs/adr/ADR-NNN-title.md
7. Branch: evolution/sprint-N-arch
8. gh pr create --base main --title "[Evolution] Sprint N Architecture"
9. Post PR link + key decisions as comment on this issue
10. Set issue to done

**Done when:** PR open + ARCHITECTURE.md updated with sprint section.
```

**Wait for:** Issue status = `done`, PR open.

---

## Phase 3: PLAN (You — CEO)

After reading RESEARCH.md + ARCHITECTURE.md:
1. Create `docs/PRD.md` (use template below)
2. Create Paperclip issues as BMAD stories for each deliverable

**PRD Template:**
```markdown
# Sprint N — PRD
## Goal
[One sentence]
## Acceptance Criteria
- [ ] [measurable outcome]
## Stories
| Story | Assignee | Branch |
|-------|----------|--------|
| EVO-N: [title] | Framework Engineer | framework/sprint-N-[desc] |
## Out of Scope
```

**Issue payload:**
```json
{
  "title": "EVO-N: [Story title]",
  "description": "[BMAD story format — see CLAUDE.md]",
  "projectId": "3644edf4-e722-4519-8ca7-f6c8cb9c1039",
  "goalId": "115608ec-2581-469e-b269-30d6ad0032d1",
  "assigneeAgentId": "<AGENT_ID>",
  "status": "todo"
}
```

---

## Phase 4: DEVELOP (Framework Engineer)

**Trigger:** Post directive on Framework Engineer's issue with:
```
BMAD Sprint N — Development

You are Amelia (Developer). Your story:
[Paste full BMAD story from PRD]

1. Read docs/ARCHITECTURE.md before touching any code
2. PAUL Loop:
   - PLAN: Write 3-5 bullet implementation plan as comment
   - APPLY: Implement, commit with [Framework] prefix after each logical unit
   - UNIFY: Clean up, ensure pytest passes
3. Branch: framework/sprint-N-[desc]
4. gh pr create --base main --title "[Framework] ..."
5. Post PR link on this issue
6. Wait for QA Engineer approval before merging
7. Set issue to done after PR merged

**QA Engineer ID:** d80cf380-d996-4070-9430-78c1431d490a
```

---

## Phase 5: BENCHMARK (Benchmark Engineer)

**Trigger:** Post directive after Framework PR is merged:
```
BMAD Sprint N — Benchmark Validation

You are the Benchmark Analyst. After Sprint N framework changes:

1. git checkout main && git pull origin main
2. python -m benchmark.runner
3. Save: results/benchmarks/sprint-N-results.json
4. python -m benchmark.visualizer
5. Write docs/benchmarks/sprint-N-summary.md
6. Compare to sprint-(N-1) — flag ANY regression immediately
7. Branch: benchmark/sprint-N-results
8. gh pr create --base main
9. Post one-line delta: "Score: X → Y (+Z%)"
10. Set issue to done (ONLY if no regressions)

**Regression protocol:** If any metric drops, post IMMEDIATE comment and DO NOT set to done.
```

---

## Phase 6: QA GATE (QA Engineer)

QA Engineer monitors PRs continuously. For each open PR:
```
PR Review Checklist:
- [ ] Tests exist for changed code
- [ ] pytest passes
- [ ] Coverage didn't drop
- [ ] Acceptance criteria met
- [ ] No direct main commits

Action: gh pr review <PR#> --approve (or --request-changes)
After approval: gh pr merge <PR#> --squash --delete-branch
```

**Formal gate directive (post when all dev PRs are ready for final QA pass):**
```
BMAD Sprint N — QA Final Gate

You are Quinn (QA). Final sprint validation:
1. git checkout main && git pull origin main
2. pytest tests/ -v --tb=short
3. pytest --cov=evoforge tests/ > results/coverage/sprint-N.txt
4. Verify all sprint acceptance criteria in docs/PRD.md
5. Post pass/fail verdict as comment here
6. Set issue to done if PASS

Nothing ships without your sign-off.
```

---

## Phase 7: DOCUMENT (Publisher Agent)

**Trigger:** Post directive after QA gate passes:
```
BMAD Sprint N — Documentation

You are Paige (Tech Writer). Document what shipped:

1. git checkout main && git pull origin main
2. gh pr list --state closed --limit 20 (see what merged)
3. Read docs/benchmarks/sprint-N-summary.md for metrics
4. Update CHANGELOG.md — add Sprint N entry
5. Update README.md — new features, updated benchmark graphs
6. Update any stale docs/
7. Branch: publisher/sprint-N-docs
8. gh pr create --base main
9. Post PR link + "Updated: README, CHANGELOG, [other files]"
10. Set issue to done
```

---

## Phase 8: RETRO (You — CEO)

After Publisher PR merged:
1. `git pull origin main`
2. Write `iteration-summaries/iter-N.md`:
```markdown
# Sprint N Retrospective
## Date
## What Shipped
## Benchmark Delta
## What Worked
## What Failed / Blockers
## Human Interventions (target: 0)
## Lessons for Sprint N+1
## Next Sprint Preview
```
3. Post retro summary as comment on sprint tracking issue
4. Plan Phase 1 of next sprint

---

## Adapter Config (9router_local ONLY)
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
  }
}
```
**NEVER switch to claude_local.**

## Paperclip API
```bash
# Base
http://localhost:3100/api

# Create issue
curl -X POST http://localhost:3100/api/issues \
  -H 'Content-Type: application/json' \
  -H 'Cookie: better-auth.session_token=<TOKEN>' \
  -H 'Origin: http://localhost:3100' \
  -d '{...}' | toon

# Comment
curl -X POST http://localhost:3100/api/issues/<ID>/comments \
  -H 'Content-Type: application/json' \
  -H 'Cookie: better-auth.session_token=<TOKEN>' \
  -H 'Origin: http://localhost:3100' \
  -d '{"body":"..."}' | toon

# Status update
curl -X PATCH http://localhost:3100/api/issues/<ID> \
  -H 'Content-Type: application/json' \
  -H 'Cookie: better-auth.session_token=<TOKEN>' \
  -H 'Origin: http://localhost:3100' \
  -d '{"status":"done"}' | toon

# List issues
curl -s 'http://localhost:3100/api/companies/553fc920-ea5f-47c7-b36f-b551cdbf31fd/issues?limit=50' | toon

# List agents
curl -s 'http://localhost:3100/api/companies/553fc920-ea5f-47c7-b36f-b551cdbf31fd/agents' | toon
```

## Git Rules (include in every directive)
1. NEVER commit to `main` directly
2. Always `git checkout main && git pull origin main` before branching
3. Branch: `<role>/<sprint-N-desc>`
4. Always create PR with `gh pr create --base main`
5. Never force push
6. Wait for QA approval before merging
7. Squash merge + delete branch after

## BMAD Artifacts Reference
| Artifact | Location | Owner |
|----------|----------|-------|
| Research Brief | `RESEARCH.md`, `docs/briefs/` | Research Engineer |
| Architecture Doc | `docs/ARCHITECTURE.md` | Evolution Agent |
| ADRs | `docs/adr/` | Evolution Agent |
| PRD | `docs/PRD.md` | CEO |
| User Stories | `docs/stories/` | CEO |
| Benchmark Results | `results/benchmarks/` | Benchmark Engineer |
| Benchmark Graphs | `results/graphs/` | Benchmark Engineer |
| Test Suite | `tests/` | QA Engineer |
| Coverage Reports | `results/coverage/` | QA Engineer |
| README / Docs | `README.md`, `docs/` | Publisher Agent |
| CHANGELOG | `CHANGELOG.md` | Publisher Agent |
| Retrospectives | `iteration-summaries/` | CEO |
