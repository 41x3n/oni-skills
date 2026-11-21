# Working on oni

You are editing a Claude Code / Codex skill pack. `README.md` explains what it
is for a human deciding whether to install it. This file is for you, changing it.

## The one invariant

**Everything in a `SKILL.md` is paid for on every invocation. Everything in
`references/` is free until read.**

That is the whole design. A `SKILL.md` is a router: the gate, the short rules,
and a table saying which reference to open. Depth goes in `references/`.

Current budget, and it is a budget, not a description (tokens estimated as
characters / 4, the same method as the check below):

| | tokens |
|---|---|
| any single `SKILL.md` | < 650 |
| all 10 skills, if every one loaded | ~6,000 |
| all references, on demand | ~18,600 |

Check before you commit:

```bash
for f in skills/*/SKILL.md; do echo "$(( $(wc -c < "$f") / 4 ))t $f"; done
```

If a skill crosses 650, move prose to `references/`, do not trim the gate.

One standing exception: `guard` sits at ~670. Unlike every other skill it needs
a trigger checklist in the always-loaded body — a bug announces itself, a
security-relevant change does not — and moving that to a reference would mean
the skill never fires. An exception needs a reason recorded here; raising the
number for everyone is not an option.

## Repository map

```
skills/<name>/SKILL.md          the always-loaded router. Budgeted.
skills/<name>/references/*.md   depth, loaded only when the SKILL.md says to
hooks/oni-router.sh             Claude: SessionStart hook output
hooks/oni-router.md             Codex: imported by ~/.codex/AGENTS.md
hooks/hooks.json                wires the hook when installed as a plugin
scripts/scan.py                 the regex behind every language rule
scripts/baseline.json           committed counts from the author's private repos; no roots
scripts/baseline.local.json     per-machine counts, gitignored, wins over the above
scripts/measure.py              consumption profile the pack's design rests on
scripts/doctor.sh               is this machine actually set up
scripts/install*.sh             linking and hook wiring, per harness
evals/<case>/prompt.md          one case per gate
evals/<case>/graders/*.md       frontmatter needs `type:` — see below
.github/workflows/test.yml      CI: unit tests and shell syntax checks
```

`plan` creates `docs/work/YYYY-MM-DD-<slug>.md` in the user's project, one file
per feature with a 200-line cap. No `docs/work/` is shipped in this repo.

## Rules for changing a language skill

**A rule cites a count, and the count must be checkable.**

1. Every rule in `oni-go`, `oni-py`, `oni-ts` states how many times the pattern
   appears in the codebase it was mined from. The committed counts come from
   the author's private production repos, so nobody else can re-run them; a
   contributor proposing a new rule cites counts from a scan of their own
   repos and says which repos those are.
2. That count must come from `scripts/scan.py`, not from reading code and
   estimating. Add the pattern to `PATTERNS` (or `CUSTOM`) with a direction of
   `bad` or `good` before you write the rule.
3. Cited counts must match the baseline. When prose and scan disagree, **the
   prose is wrong.** This has already happened once: four counts were off
   because the first scan included test files and used looser regexes.
4. A rule with no pattern behind it cannot be checked and will rot. Do not add
   one.

Verify after editing:

```bash
python3 scripts/scan.py --roots ~/your/repos --write-baseline   # once, writes baseline.local.json
python3 scripts/scan.py                                         # later runs reuse its roots
```

Never run `--write-baseline` to make a disagreement go away. That erases the
drift before anyone reads it, which is the one thing `oni-tune` forbids.

## Rules for changing a process skill

`spark`, `plan`, `build`, `debug`, `ship` each carry exactly one gate, stated
with its reason in one clause. The reason is load-bearing: compression that
removes *why* a gate exists measurably weakens compliance. Cut the prose around
a gate, never the gate or its reason.

If you add a skill:

1. Add it to the routing table in **both** `hooks/oni-router.sh` and
   `hooks/oni-router.md`. A skill absent from the router is a skill that never
   fires — this was measured, not assumed: without the router a feature request
   produced code immediately and no skill was invoked at all.
2. Add a row to the table in `README.md`.
3. Add an eval case if it carries a gate.

## Frontmatter

`SKILL.md`:

```yaml
---
name: <matches the directory name>
description: <when to use it, trigger words included — this is what the model
  sees in the skill list, and it is paid for every session, so keep it tight>
---
```

Eval grader, in `evals/<case>/graders/*.md`:

```yaml
---
type: llm | tool_used | regex | tool_order | file_exists | baseline
name: <grader name>
---
```

`type:` is required and the harness rejects the file without it. Under a
with-without ablation, current evaluators automatically treat `tool_used: Skill`
as a "did the pack fire" indicator rather than part of the score.

## Verifying a change

```bash
./scripts/doctor.sh                          # install state on this machine
python3 scripts/scan.py                      # rule drift (needs a local baseline)
python3 -m unittest discover -s scripts -p 'test_*.py'
claude plugin validate .
bash hooks/oni-router.sh                     # router output, ~1,000 tokens
claude plugin eval . --threshold 0 --no-publish
```

The eval spawns real `claude` children in a sealed sandbox, so it needs
`ANTHROPIC_API_KEY` exported — a keyring OAuth session is not visible inside
the sandbox. It defaults to `--ablation with-without`, which also runs each
case *without* the pack. That delta is the number that matters: a case scoring
the same on both arms means the pack did nothing.

## Things that have already gone wrong here

Do not re-introduce these.

- **Absolute paths in config.** The `SessionStart` hook command is an absolute
  path and differs per machine. `install-hook.sh` derives it from its own
  checkout. Never hardcode one.
- **A baseline from someone else's repos.** `scan.py` records `_roots` and
  warns when you scan something else. Writes go to `baseline.local.json`.
- **Private paths in the committed baseline.** `baseline.json` ships with
  `"_roots": []`. Never commit a baseline that records your machine's paths.
- **Claiming code is dead without checking tests.** `onComplete` was called
  dead code in a review; two tests used it as a completion signal.
- **Trusting one scan.** Refining the scan cut four planned rules that did not
  actually fire.

## Style

Follow what is there. Declarative, no hedging, no "you should consider". A rule
is an instruction with a reason, in that order. Tables over prose when the
content is a mapping. No emoji. Code blocks show the right way, and the wrong
way only when the contrast is the point.

Feature work on this pack runs through `plan`'s format and stays under its own
200-line cap. Those WORK.md files are working notes and are not committed.
