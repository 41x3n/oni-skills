# oni-tune maintenance

## Baselines on a machine that did not mine the rules

`scripts/baseline.json` is committed and holds counts mined from the author's
private production repos. It records no roots, so nobody else can re-run it.
Those numbers describe someone else's code, and every drift verdict computed
against them is noise until you write your own baseline.

Writing a baseline creates `scripts/baseline.local.json`, which is gitignored
and read in preference to the committed one. Two machines therefore never fight
over a single file, and a clone never silently inherits foreign counts.

```bash
python3 scripts/scan.py --roots ~/path/to/your/repos --write-baseline
```

Roots resolve in this order, so after the first write no path is needed again:

1. `--roots`
2. `$ONI_SCAN_ROOTS` (path-separator delimited)
3. `_roots` recorded inside the baseline

Scanning roots the baseline was not built from prints a warning naming both
sets of paths and declaring the verdicts below it meaningless. Do not read past
that warning — re-baseline first.

## Adding a pattern

A new language rule needs a new entry in `PATTERNS` in `scripts/scan.py` before
the rule text is written:

```python
("double_cast", r"as unknown as", "bad"),
```

Direction is `bad` (a rule fires while the count is above zero) or `good` (a
practice that should stay high; the tool flags it when it halves). Evidence that
needs per-file logic rather than a flat count goes in `CUSTOM` instead — see
`_py_untyped_params` and `_go_io_without_ctx` for the shape.

A rule with no pattern behind it cannot be checked and will rot. Do not add one.

## Why the tool refuses to re-baseline for you

Writing a fresh baseline makes every disagreement disappear, including the ones
nobody has read yet. That converts a drift report into a silent overwrite of the
evidence. Re-baseline only after the `SKILL.md` edits are approved, never as a
way to get to a clean run.

## What a stale count actually costs

The rules carry weight because they cite real counts from real code. A rule
asserting a number that is no longer true is worse than no rule: it is the exact
property that makes a generic best-practice pack easy to ignore. One pass of
this skill has already corrected four counts that were wrong on day one — the
first scan included test files and used looser regexes than the committed one.
