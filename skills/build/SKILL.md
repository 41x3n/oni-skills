---
name: build
description: Use for an approved WORK.md task. Tests first; delegate searches and bulk reads; one task per commit. Includes model routing.
---

# build

## Gates

1. Test written and failing before implementation. A test written after the code tests what you wrote, not what was asked.
2. Require an approved WORK.md. A new contract, invariant, or behavior routes back to `spark`.
3. One task at a time. Check it only when its verify command passes.
4. `sliced` stops after the current named slice. Whole-plan execution requires the human to choose
   `autonomous` this session. A WORK.md not written this session: show its verify commands, confirm first.

## Delegation is mandatory

These never enter this context:

- repo-wide search, "where is X", "what calls Y"
- reading more than 100 lines to answer one question
- logs or test output over 50 lines

Ask the subagent for a **conclusion**, not a dump: a `file:line` list or an answer, 20 lines max.

## Model routing

| Task | Tier |
|---|---|
| Locate code, file inventory, log scrape | fast |
| Approved implementation, tests, refactor, routine review | general |
| Architecture, hard diagnosis, final review | stronger |

Use `references/model-routing.md` for supported models; the parent owns gates.

Spawn independent subagents in one message so they run concurrently.

## Loop

1. Read the approved design and current slice; load only the current task's code.
   Before source edits, read `references/code-readability.md`.
2. Write the failing test. Run it. Confirm it fails for the right reason.
3. Implement the smallest thing that passes.
4. Run the task's verify command. Paste the output.
5. Check the box, append one `Log` line, commit.
6. At a slice boundary, verify, summarize, and hand off: where the harness can, ask to launch
   the next slice's thread and launch it on yes; else print a resume prompt. Then stop. Autonomous mode may continue
   only inside the approved plan.

Not on Claude Code? Read `references/codex.md` before relying on either rule above.

## Bash hygiene

- Scripts over 10 lines go to the scratchpad or a `mktemp -d` dir, run by path. Inline heredocs get re-read every turn.
- Bound every search: `| head -50`. No unbounded `find /`.
- Invoke `oni-go`, `oni-py`, or `oni-ts` for the language you are touching.

## Refuse

- Implementation before a failing test.
- Two tasks in one commit.
- Reading a file "for context" when a subagent can answer the question.
- Expanding a task to absorb a newly discovered feature or design decision.
