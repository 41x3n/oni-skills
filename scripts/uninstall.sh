#!/usr/bin/env bash
# Remove oni skill links. Only ever removes symlinks that point into this pack,
# so a real directory that happens to share a name is never touched.
#   ./scripts/uninstall.sh             both harnesses
#   ./scripts/uninstall.sh claude      one
#   DRY_RUN=1 ./scripts/uninstall.sh   show what would go
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TARGETS=("${@:-both}")
[[ "${TARGETS[0]}" == "both" ]] && TARGETS=(claude codex)
removed=0

for target in "${TARGETS[@]}"; do
  case "$target" in
    claude) dir="$HOME/.claude/skills" ;;
    codex)  dir="$HOME/.codex/skills" ;;
    *) echo "unknown target: $target (claude|codex)" >&2; exit 2 ;;
  esac
  [[ -d "$dir" ]] || continue

  for link in "$dir"/*; do
    [[ -L "$link" ]] || continue
    dest="$(cd "$(dirname "$link")" && readlink "$link")"
    case "$dest" in
      "$PACK"/*) ;;
      *) continue ;;
    esac
    if [[ -n "${DRY_RUN:-}" ]]; then
      echo "would remove $link"
    else
      rm "$link"
      echo "removed $link"
    fi
    removed=$((removed + 1))
  done
done

if [[ "$removed" -eq 0 ]]; then
  echo "nothing linked from $PACK"
else
  echo
  echo "$removed link(s) handled. The repo is untouched — re-run install.sh to restore."
  echo "Router hooks are separate. Remove them with:"
  echo "  ./scripts/install-hook.sh --remove         (Claude Code, ~/.claude/settings.json)"
  echo "  ./scripts/install-hook-codex.sh --remove   (Codex, ~/.codex/AGENTS.md)"
fi
