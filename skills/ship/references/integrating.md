# Integrating finished work

The mechanics behind `ship` step 4. The gates are in `SKILL.md`; this is how to
execute each path without losing anything.

## Detect the workspace first

What is possible depends on where you are, so establish it before offering a
menu:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
WORKTREE_PATH=$(git rev-parse --show-toplevel)   # capture now; you will cd later
BRANCH=$(git branch --show-current)              # empty means detached HEAD
```

| State | Offer | Cleanup |
|---|---|---|
| `GIT_DIR == GIT_COMMON` | all three options | nothing to clean |
| differ, named branch | all three options | remove the worktree after a green merge |
| differ, `BRANCH` empty | options 2 and 3 only | leave it — externally managed |

After any green merge the user asked for, also sync the local base so the next task does not start
from a stale checkout: `git fetch origin && git switch <base> && git pull --ff-only`, then delete the
merged local branch (`git branch -d <branch>`).

A submodule also reports differing dirs. `git rev-parse --show-superproject-working-tree` returning a path means submodule, not worktree; treat it as a normal repo.

Detached HEAD usually means an externally managed workspace — a Codex App
worktree, a CI checkout. You cannot merge locally from there and you must not
delete it.

## Base branch

Take it from the plan, the branch's upstream, or the conversation. If none of
those settle it, ask outright:

> This forked from `main` — correct?

Do not infer it from the default branch. A feature branched off a release
branch, merged into the default branch, is a mess to unpick and the mistake is
invisible until someone notices the diff is enormous.

## Option 1 — merge locally

```bash
# Run from the main checkout, not the worktree you are about to remove.
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel) || exit 1
cd "$MAIN_ROOT" || exit 1

MERGE_STATUS=$(git status --porcelain) || exit 1
if [[ -n "$MERGE_STATUS" ]]; then
  echo "Stop: preserve local edits and untracked files before merging." >&2
  exit 1
fi
git checkout <base> || exit 1
git pull --ff-only || exit 1
PRE_MERGE_HEAD=$(git rev-parse HEAD) || exit 1
printf 'Pre-merge commit: %s\n' "$PRE_MERGE_HEAD"
git merge <feature> || exit 1

<the project's test command> || {
  echo "Stop: merged tests failed. Preserve work; do not reset or clean up." >&2
  exit 1
}
```

**The order is the gate.** Tests passed on the branch; that says nothing about
the branch merged into a base that has moved. Only once the merged tree is
green:

```bash
git worktree remove "$WORKTREE_PATH"    # if there was one
git branch -d <feature>                 # -d, never -D: it refuses if unmerged
```

Record the printed pre-merge commit in the work log before cleanup. It is the
exact recovery target, including when a fast-forward adds several commits.

If the merge or merged tests fail, stop. Keep the worktree and branch, inspect
the failure, and preserve any edits or files created since the merge began.
Do not push, reset, or delete anything automatically.

`git merge --abort` applies only while a merge is in progress. Check for
`MERGE_HEAD` with `git rev-parse --verify MERGE_HEAD` before using it, and
preserve later work first. It cannot undo a completed merge.

For a completed merge, compare HEAD with the recorded pre-merge commit. Only
recover to that exact commit when the user requests recovery and all later
work has been preserved. `HEAD~1` is not a reliable recovery target: a
fast-forward can contain several commits. A hard reset also discards tracked
edits. Keeping the branch and worktree makes investigation and recovery possible.

`git branch -d` over `-D` for the same reason — it refuses to delete a branch
whose commits are not merged, which is a free safety net.

## Option 2 — push and open a PR

```bash
git push -u origin <feature>

# From a detached HEAD, name the branch explicitly:
git push origin HEAD:refs/heads/<new-branch>
```

Open the PR against the confirmed base with the forge's CLI (`gh pr create`),
or the creation URL most forges print on push. Follow the repo's PR template if
it has one. Report the URL.

**Keep the worktree.** Review feedback gets addressed there; removing it means
recreating it an hour later.

## Option 3 — leave it

Report the branch name and, if there is one, the worktree path. Nothing else.

## If asked to discard

Only ever in response to an explicit request — it is never one of the offered
options, and never inferred from "this didn't work out".

```bash
git worktree remove --force "$WORKTREE_PATH"
git branch -D <feature>
```

Say what is being destroyed and confirm before running it. Unmerged commits are
recoverable from the reflog for a while, but a removed worktree's uncommitted
changes are not recoverable at all.

## Sandboxed workspaces

If the environment blocks branch or push operations — a detached HEAD in a
worktree the harness owns — commit the work, then hand back what the human
needs to finish it themselves: a suggested branch name, the commit messages,
and a PR description. Running tests and staging files still works.
