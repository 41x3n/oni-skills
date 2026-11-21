# Security policy

## Reporting a vulnerability

Private vulnerability reporting is enabled for this repository. Report security issues through
a GitHub security advisory: <https://github.com/41x3n/oni-skills/security/advisories/new>.

Do not open a public issue for a vulnerability. Include the affected file, the steps to reproduce,
and the impact you expect. You should get a reply within a week.

## Scope

In scope:

- Install and uninstall scripts in `scripts/` that edit user configuration:
  `~/.claude/settings.json`, `~/.codex/AGENTS.md`, and symlinks under `~/.claude/skills` and
  `~/.codex/skills`.
- The router hook (`hooks/oni-router.sh`, `hooks/hooks.json`) that runs at every session start.
- `scripts/scan.py` and `scripts/measure.py`, which read local files.

Examples: command injection through a checkout path, deleting or corrupting configuration the
scripts do not own, or following symlinks outside the intended directories.

Out of scope: the behavior of the underlying models, and skill text that a model chooses not to
follow.

## Supported versions

The latest release (v0.1.0 onward) and `main` receive fixes.

## Supply chain

A plugin install with auto-update enabled runs the latest `main`. To control what runs, disable
auto-update for this marketplace and review the diff before each `/plugin update`, or clone the
repository and check out a signed release tag.
