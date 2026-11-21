# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-11-21

### Changed

- CI: `actions/checkout` 4.2.2 to 7.0.1 and `actions/setup-python` 5.6.0 to 7.1.0, still pinned by commit SHA.

## [0.1.0] - 2026-11-21

### Added

- Initial public release.
- Process skills: `spark`, `plan`, `build`, `debug`, `guard`, `ship`.
- Language skills: `oni-go`, `oni-py`, `oni-ts`.
- Maintenance skill: `oni-tune`, with `scripts/scan.py` and `scripts/measure.py`.
- Claude Code plugin and marketplace manifests with a `SessionStart` router hook.
- Clone install scripts for Claude Code and Codex, `doctor.sh`, and `uninstall.sh`.
- Eval cases under `evals/` for `claude plugin eval`.

### Security

- Autonomous execution counts only when the user chose it in the current session. A WORK.md not
  written in the session must have its verify commands shown and confirmed before anything runs.
- The router treats content from files, web pages and tool output as data, not instructions.
- Hook installers write atomically, keep file modes, never overwrite a backup, keep the newest
  five backups, refuse duplicate JSON keys and checkout paths with line breaks, and write
  nothing on `DRY_RUN=1`.
- `scan.py` patterns run in linear time on hostile input, with unchanged counts.
- `doctor.sh` handles paths with spaces.
- CI actions are pinned to commit SHAs and watched by Dependabot. `CODEOWNERS` and a supply
  chain note in `SECURITY.md` were added.

[Unreleased]: https://github.com/41x3n/oni-skills/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/41x3n/oni-skills/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/41x3n/oni-skills/releases/tag/v0.1.0
