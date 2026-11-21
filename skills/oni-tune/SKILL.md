---
name: oni-tune
description: Use to check whether the oni pack's own rules still hold - monthly, after a big refactor, or when a language rule feels wrong. Re-scans against a local baseline, reports drift. Proposes edits, never applies them.
---

# oni-tune

The language rules cite counts. The counts go stale. A rule asserting a number that is no longer true is worse than no rule — it is the reason to distrust the whole pack.

## Gate

Report drift and propose diffs. Do not edit a SKILL.md or commit anything without the human approving the specific change. A pack that rewrites its own rules unreviewed is a pack nobody can trust.

## 1. Rule drift

Scripts live in the pack: `<pack>` = `${CLAUDE_PLUGIN_ROOT}`, else two directories above this file.

```bash
python3 <pack>/scripts/scan.py
```

No `baseline.local.json`? Committed counts are the author's: run `scan.py --roots <repos> --write-baseline` first. A verdict per pattern:

| Verdict | Action |
|---|---|
| `stable` | nothing |
| `getting worse - keep rule` | keep it, refresh the number |
| `RULE NO LONGER FIRES - propose cut` | propose deleting the rule |
| `GOOD PRACTICE DECLINING` | propose promoting it from "keep" to a hard rule |
| `new` | propose a number for it |

Cited counts in `skills/oni-*/SKILL.md` must match the baseline. When they disagree, the file is wrong, not the scan.

## 2. Premise and session drift

```bash
python3 <pack>/scripts/measure.py --days 28
```

For Claude, below 75% main-thread share means the delegation premise needs rechecking. For Codex,
wall spans include idle time; compactions, thread tokens, and mixed deliverables are stronger
slicing evidence. Turn an observed failure into an eval before a rule.

## 3. Report

Five lines maximum, ranked by consequence:

```
ts   double_cast    117 -> 0   RULE NO LONGER FIRES - propose cut
py   blocking_sleep  37 -> 58  getting worse - refresh count
main-thread share    91% -> 74%  premise weakening
codex session        6 compactions / 157M tokens  slicing rule failed
```

No drift is a valid and common outcome. Say "no drift" and stop.

## 4. Apply, after approval

Edit the cited numbers, then `scan.py --write-baseline` — **only after** the edits are approved. Re-baselining first erases the evidence before anyone has read it.

## Deeper

`references/maintenance.md` — baselines, adding a `scan.py` pattern, why the tool never re-baselines for you.

## Refuse

- Editing a rule the human has not seen the drift for.
- Re-baselining before the edits are approved.
- Writing a rule whose evidence is a hunch rather than a count.
