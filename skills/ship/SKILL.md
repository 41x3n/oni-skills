---
name: ship
description: Use before claiming completion, committing, merging, finishing a worktree, or opening a PR. Evidence before assertion; ends the session.
---

# ship

## Gate

No "done", "fixed", "passing", or "working" without command output pasted from this session. An unverified completion claim is the most expensive sentence available to you.

## 1. Verify

Run and paste each result:

- the full test suite
- the linter / type checker
- the project build

Nothing passes by assumption. Report a skipped step as skipped.

## 2. Reconcile against WORK.md

Every task checked? Anything done that is not in the file, or in the file and not done? State it plainly. Set `Status: shipped`.

## 3. Review

Delegate correctness and simplification review using `build`'s model routing: one line per finding, severity tagged. Fix real findings; explain skipped ones.
For code changes, read `../build/references/code-readability.md` and review the diff against it.

## 3b. Security

Diff touches a route, handler, auth, secrets, config you do not own, or builds a command from a value? Invoke `guard` first.

## 4. Integrate

**Detect the workspace first.** Normal repo, worktree, or detached HEAD — a detached HEAD cannot merge locally, so offering it gives a confusing failure, not a choice.

**Confirm the base branch** with the user: it is not always the default, and merging into the wrong one is expensive to undo.

Then offer, and wait — never push or merge unasked:

1. merge to `<base>` locally
2. push and open a PR
3. leave the branch alone

Detached HEAD gets 2 and 3 only.

**On merge: verify, then delete. Never the reverse.** Re-run the suite *on the merged result*, then fast-forward local `<base>` and delete the merged branch and worktree. Tests passing before the merge say nothing about the merge, and deleting first is how work is lost.

`references/integrating.md`: commands per path, worktree cleanup, detached HEAD, sandboxed workspaces.

## 5. End the session

State what works and the command to run. Stop.

In sliced execution, hand off the next slice with the WORK.md path and a resume prompt: where the harness can, ask to launch its thread and launch it on yes; else print the prompt. Then stop.

## Refuse

- An unverified success claim.
- Pushing or merging without being asked.
- Deleting a branch or worktree before the merged result is green.
- Merging into a base nobody confirmed.
- Continuing into another slice without approved autonomous execution.
- Continuing into a new deliverable in the same session.
