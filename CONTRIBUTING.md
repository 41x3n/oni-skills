# Contributing to oni

Thanks for helping. This pack is small on purpose, so most changes are small too.

If you are an agent (Claude Code, Codex, or similar) making the change, read
[CLAUDE.md](CLAUDE.md) first. It has the full rules; this file is the short version for people.

## Run the checks

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'   # unit tests, Python 3.9+
claude plugin validate .                                 # plugin and marketplace manifests
bash -n scripts/*.sh hooks/*.sh                          # shell syntax
```

One test (`test_upstream_examples.py`) needs Node 22.7 or newer and is skipped without it.
CI runs the same tests on Ubuntu and macOS.

Never test the install scripts against your real home directory. Use a throwaway one:

```bash
(
  export HOME="$(mktemp -d)" && mkdir "$HOME/.claude"
  ./scripts/install.sh claude && ./scripts/install-hook.sh && ./scripts/doctor.sh
  ./scripts/uninstall.sh && ./scripts/install-hook.sh --remove
  rm -rf "$HOME"
)
```

If you change prompts or skills and have an API key, also run
`claude plugin eval . --threshold 0 --no-publish` and report the with/without delta.

## Rules that matter

- **Token budget.** Every `SKILL.md` is loaded whenever its skill fires, so each one stays under
  650 tokens (characters / 4). Depth goes in `references/`, which costs nothing until read. Check:

  ```bash
  for f in skills/*/SKILL.md; do echo "$(( $(wc -c < "$f") / 4 ))t $f"; done
  ```

- **A language rule cites a scan count.** A new rule in `oni-go`, `oni-py`, or `oni-ts` needs a
  pattern in `scripts/scan.py` first, and the rule states the count that pattern produced. Say which
  codebases you scanned. A rule with no pattern behind it cannot be checked and will not be merged.
- **Gates keep their reason.** Process skills carry one gate each, with its reason in one clause.
  Trim prose around a gate, never the gate or its reason.
- **New skills go in the router.** Add them to both `hooks/oni-router.sh` and
  `hooks/oni-router.md`, and to the table in `README.md`.
- **No private paths.** Never commit a baseline or config containing paths from your machine.

## Pull requests

- One change per pull request, with a short description of what and why.
- Paste the output of the checks above.
- For a skill or router change, say what behavior you expect to change and how you checked it
  (an eval run, or a transcript excerpt).
- Update `CHANGELOG.md` under `Unreleased`.
- Plain, professional English in docs. No emoji.
