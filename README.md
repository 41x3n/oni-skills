# oni

A lean engineering skill pack for Claude Code and Codex.

Everything in the context window is re-read on every later turn, so the costly mistake is not a
long skill. It is a 30K tool result that lands early and rides along for ninety turns. oni keeps
bulk reading in cheap subagents, puts hard gates on design and completion, and ends sessions
before they bloat.

## Quickstart

In Claude Code, run these one at a time:

```
/plugin marketplace add 41x3n/oni-skills
```

```
/plugin install oni@oni-skills
```

Open a **new session** in one of your repos and ask for a feature. oni should come back with a
design or a question, and edit nothing until you approve.

Codex, clone installs, updating and uninstalling: [docs/install.md](docs/install.md).

## Skills

| Skill | Use it for | Gate |
|---|---|---|
| `spark` | Any design or new feature | No code until you approve |
| `plan` | Turning an approved design into tasks | One `WORK.md`, 200 lines max |
| `build` | Implementing one task | Failing test first; bulk reading delegated |
| `debug` | Any bug or test failure | Root cause named before any fix |
| `guard` | Any change to an external input path | Entry, validation and reader named |
| `ship` | Verifying, merging, finishing a branch | No success claim without pasted output |
| `oni-go` | Writing or reviewing Go | |
| `oni-py` | Writing or reviewing Python | |
| `oni-ts` | Writing or reviewing TypeScript | |
| `oni-tune` | Checking whether the pack's own rules still hold | Proposes edits, never applies |

All ten `SKILL.md` files together are about 6,000 tokens. Their detailed `references/` load only
when needed.

## What a gate looks like

Asked to "add a --retry flag to the uploader so failed uploads retry three times with backoff":

```
spark → bounded. Repo read: main.go (21 lines), internal/upload/upload.go (33 lines).

Blocker found before design. Body is os.Stdin, an io.Reader. First attempt
drains it. Retry attempt 2 uploads zero bytes and likely gets a 200.

Q1 of ~2 — how to make body replayable?
  A (rec) io.ReadAll into memory ... OOM on uploads bigger than RAM
  B       spool to temp file      ... cleanup + disk-full path
  C       retry only if Seeker    ... defeats the ask
```

It stops there and writes nothing until you pick.

## Requirements

Claude Code with plugin support, or Codex. `bash` and `python3` 3.9+. macOS or Linux.

## Learn more

- [How it works](docs/how-it-works.md): the feature chain, delegation, model routing, language rules
- [Install](docs/install.md): Codex, clone installs, updating, uninstalling
- [Measurements](docs/measurements.md): the numbers behind the design
- [Contributing](CONTRIBUTING.md)

## License

MIT
