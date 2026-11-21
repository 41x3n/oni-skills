# Install

## Requirements

- Claude Code with plugin support, or Codex.
- `bash`. The router hook and install scripts are bash scripts.
- `python3` 3.9 or newer for the scripts in `scripts/`.
- macOS or Linux. Windows is not supported, because the hook runs bash.
- Node 22.7 or newer only for one optional test, which is skipped otherwise.

## Claude Code plugin

Run these one at a time:

```
/plugin marketplace add 41x3n/oni-skills
```

```
/plugin install oni@oni-skills
```

The plugin wires its own `SessionStart` hook. To check it landed:

1. Run `/plugin` and confirm `oni` is enabled.
2. Start a new session. The hook runs at session start.
3. Ask for a feature. A design or a question should come back, with no file edits.

If it starts editing files instead, the hook did not load. Confirm the plugin is enabled, then
start another new session.

## Claude Code from a clone

Use this if you want to edit the pack.

```bash
git clone https://github.com/41x3n/oni-skills ~/src/oni-skills
cd ~/src/oni-skills
./scripts/install.sh claude     # symlinks skills into ~/.claude/skills
./scripts/install-hook.sh       # adds the router hook to ~/.claude/settings.json
./scripts/doctor.sh             # read-only check of the install
```

`install-hook.sh` backs up `settings.json`, merges instead of replacing, is safe to re-run, and
takes `--remove`. `DRY_RUN=1` prints the result without writing. `doctor.sh` changes nothing. It
reports problems and prints the fix.

## Codex

Codex has no plugin system and no `SessionStart` hook, so it always uses a clone.

```bash
git clone https://github.com/41x3n/oni-skills ~/src/oni-skills
cd ~/src/oni-skills
./scripts/install.sh codex          # links into ~/.codex/skills
./scripts/install-hook-codex.sh     # imports the router into ~/.codex/AGENTS.md
./scripts/doctor.sh
```

The router goes into `~/.codex/AGENTS.md` as one `@path` import line pointing at
`hooks/oni-router.md`. The script is idempotent, backs up `AGENTS.md`, leaves your other imports
alone, and takes `--remove`.

## Updating

Plugin, one command at a time:

```
/plugin marketplace update oni-skills
```

```
/plugin update oni@oni-skills
```

Clone:

```bash
cd ~/src/oni-skills
git pull
./scripts/install.sh        # links any new skills
./scripts/doctor.sh
```

`git pull` alone does not link a newly added skill. Run `install.sh` again. Re-run the hook
installer only if you moved the checkout, because the hook stores an absolute path.

## Uninstall

Plugin:

```
/plugin uninstall oni@oni-skills
```

```
/plugin marketplace remove oni-skills
```

Clone:

```bash
DRY_RUN=1 ./scripts/uninstall.sh          # show what would be removed
./scripts/uninstall.sh                    # remove the skill links
./scripts/install-hook.sh --remove        # Claude Code router hook
./scripts/install-hook-codex.sh --remove  # Codex router import
```

Only symlinks that point into this checkout are removed. The repo stays on disk.
