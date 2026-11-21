#!/usr/bin/env bash
# Link oni skills into Claude Code and/or Codex. Idempotent. Repoints links
# left by another oni checkout; never touches anything else.
#   ./scripts/install.sh             both harnesses
#   ./scripts/install.sh claude      one
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TARGETS=("${@:-both}")
EXPLICIT=1
[[ "${TARGETS[0]}" == "both" ]] && { TARGETS=(claude codex); EXPLICIT=0; }

for target in "${TARGETS[@]}"; do
  case "$target" in
    claude) home="$HOME/.claude" ;;
    codex)  home="$HOME/.codex" ;;
    *) echo "unknown target: $target (claude|codex)" >&2; exit 2 ;;
  esac
  dir="$home/skills"

  # A missing tool home means the tool is not installed (or never ran).
  # Skip it quietly when installing for both; fail when it was asked for.
  if [[ ! -d "$home" ]]; then
    if [[ "$EXPLICIT" -eq 1 ]]; then
      echo "$target: $home does not exist. Install and run $target once, then re-run this script." >&2
      exit 1
    fi
    echo "$target: no $home, skipping (not installed?)"
    continue
  fi
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
    echo "$target: created $dir"
  fi

  for skill in "$PACK"/skills/*/; do
    name="$(basename "$skill")"
    link="$dir/$name"
    if [[ -L "$link" ]]; then
      dest="$(readlink "$link")"
      real="$(cd "$link" 2>/dev/null && pwd -P || true)"
      if [[ "$real" == "${skill%/}" ]]; then
        echo "$target: $name already linked"
      elif [[ -z "$real" || -f "$real/../../hooks/oni-router.sh" ]]; then
        # dangling, or another oni checkout: repoint at this one
        ln -sfn "$skill" "$link"
        echo "$target: relinked $name (was $dest)"
      else
        echo "$target: $name links to $dest, not oni — left alone" >&2
      fi
    elif [[ -e "$link" ]]; then
      echo "$target: $name EXISTS and is not a symlink — left alone" >&2
    else
      ln -s "$skill" "$link"
      echo "$target: linked $name"
    fi
  done
done

echo
echo "Verify with a fresh session: the skills appear in the skill list."
echo "The router hook is NOT installed by this script: run ./scripts/install-hook.sh"
echo "(Claude Code) or ./scripts/install-hook-codex.sh (Codex)."
