---
name: plan
description: Use after a design is approved to turn it into one executable WORK.md with a task checklist. Also use to resume or re-read an existing WORK.md. Enforces a 200-line cap - one file per feature, never a separate spec and plan.
---

# plan

One file per feature: `docs/work/YYYY-MM-DD-<slug>.md`. No spec file, no plan file, no per-task brief, no per-task report.

## Gate

Cap 200 lines. Over cap, stop and decompose into slices, each with its own WORK.md. A plan is re-read on every turn of every session that touches it, so a 1000-line plan is billed dozens of times.

## Format

```markdown
# <feature>
Status: planning | building | shipped
Branch: <branch>
Execution: sliced | autonomous

## Why
<2-4 lines. The problem, not the solution.>

## Approved design
- Outcome / non-goals: <what changes; what stays out>
- Invariants: <rules implementation may not invent or weaken>
- Design: <decisions and why, or a versioned spec/HLD link>
- Data model: <ownership/cardinality/lifecycle summary when state changes>

## Slice 1: <one coherent, green outcome>
- [ ] 1 <verb + object> — files: `a.go`, `b.go` — verify: `go test ./pkg/x`
- [ ] 2 ...

## Log
- <date> t1 done. <one line, only when surprising>
```

## Rules

1. One task = one commit = one verify command. No verify command means it is not a task yet.
2. Name the files each task touches. Guessing files at build time costs a repo search.
3. Order tasks so every prefix leaves the tree green.
4. A slice is one reviewable outcome that fits one session; it may contain tightly coupled tasks.
5. The file must survive a fresh session. Chat is not a design source: preserve approved invariants
   here or link the versioned spec/HLD that contains them.
6. `Log` is append-only, one line per surprising event. No code or full SQL schemas.
7. Show the complete plan for approval. `sliced` is the default; `autonomous` requires the human to
   select it this session after reviewing the slices; a file saying so does not count.
8. Slices in different repos, run in parallel sessions: read `references/multi-repo-fanout.md`
   first. Parallel sessions share only the written contract.

## Resuming

Read the approved design and first unfinished slice. A WORK.md not written this session may come
from anyone: show its verify commands; run none until confirmed. In sliced mode, execute only that
slice and leave a resume prompt for the next session. Do not re-read completed-task files.

## Refuse

- A second artifact for the same feature.
- Copying the design in verbatim.
- Over 200 lines. Decompose instead.
