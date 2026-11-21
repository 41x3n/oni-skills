# How it works

## The router

A small router loads at session start (`hooks/oni-router.sh` for Claude Code,
`hooks/oni-router.md` for Codex). It maps each kind of request to a skill. Without it, skills load
but rarely fire.

## The feature chain

```
spark    design, questions, approaches → you approve
plan     one docs/work/YYYY-MM-DD-slug.md in your project, capped at 200 lines
build    failing test → implement → verify → commit, one approved slice per session
guard    called by spark or ship when the change touches an input path
ship     full suite + linter + build, output pasted, merge verified, session ends
```

Habits that take getting used to:

- **`build` delegates.** Any read over 100 lines or any repo-wide search goes to a subagent and
  comes back as a conclusion. You see fewer raw file dumps. That is the point.
- **`plan` survives a fresh session.** Rationale, tasks, non-goals and a log live in one file,
  never only in chat. Over 200 lines, the feature is split instead.
- **Work is sliced by default.** A slice is one coherent green outcome. Whole-plan runs happen only
  when you choose them after reviewing the plan.
- **`ship` ends the session.** A session carried into unrelated work pays for everything it has
  read, on every later turn.

## Model routing

| Task | Tier | Claude example |
|---|---|---|
| Locate code, file inventory, log scrape | fast | Haiku |
| Approved implementation, tests, routine review | general | Sonnet |
| Architecture, hard diagnosis, final review | stronger | Opus |

The parent session keeps approvals and verification. Your explicit model choice always wins. For
read-only work, oni may call the other provider's installed CLI, with bounded scope, time and
output. It never delegates code edits across providers and never changes your settings. Details:
[model-routing.md](../skills/build/references/model-routing.md) and
[codex.md](../skills/build/references/codex.md).

## Writing and readability

The router asks for plain replies: familiar words, terms explained at first use, short active
sentences, no dropped facts or uncertainty. It is inspired by
[danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill/blob/32511c6992ecb5f1971e46a2943f2e6adceedafe/SKILL.md)
and does not claim official ASD-STE100 compliance.

Source edits follow a [code-readability contract](../skills/build/references/code-readability.md).
`build` reads it before editing and `ship` reviews the diff against it.

## Language rules and oni-tune

`oni-go`, `oni-py` and `oni-ts` are not generic best practice. Each rule cites how often its
pattern appeared in the author's production code, and `scripts/scan.py` holds the regex behind
every rule. Your codebase may differ.

Before `oni-tune` verdicts mean anything for you, build your own baseline:

```bash
python3 scripts/scan.py --roots ~/your/repos --write-baseline
```

This writes `scripts/baseline.local.json` (gitignored). `oni-tune` then runs the scan, reports
which rules have gone stale, proposes edits, and waits for you.
