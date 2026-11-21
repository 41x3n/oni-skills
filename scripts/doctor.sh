#!/usr/bin/env bash
# Report whether oni is actually set up on this machine, and what would blunt it.
# Read-only: it changes nothing and prints the command for anything it flags.
#
#   ./scripts/doctor.sh
set -uo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
problems=0

ok()   { printf '  ok    %s\n' "$1"; }
warn() { printf '  WARN  %s\n' "$1"; problems=$((problems + 1)); }
fix()  { printf '        fix: %s\n' "$1"; }

# Paths go to python as argv, never spliced into source: a path containing an
# apostrophe would otherwise be executable Python.
json_ok() {
  python3 - "$1" <<'PY'
import json, sys
json.load(open(sys.argv[1]))
PY
}

# The hook command is shell-quoted, so take the last shell word rather than
# stripping a "bash " prefix off the raw string.
last_arg() {
  python3 - "$1" <<'PY'
import shlex, sys
parts = shlex.split(sys.argv[1])
print(parts[-1] if parts else "")
PY
}

# One root per line: a root may contain spaces or commas.
baseline_roots() {
  python3 - "$1" <<'PY' 2>/dev/null
import json, sys
print('\n'.join(json.load(open(sys.argv[1])).get('_roots', [])))
PY
}

echo "oni doctor — $PACK"
echo

# Installed as a plugin? Read the settings key rather than walking the plugins
# tree — that tree is gigabytes on a machine with a few marketplaces, and
# recursing it twice is what made an earlier version of this script time out.
plugin_installed=$(python3 - "$SETTINGS" <<'PY'
import json, sys
try:
    s = json.load(open(sys.argv[1]))
except Exception:
    print("no"); raise SystemExit
for k, v in (s.get("enabledPlugins") or {}).items():
    if v and k.split("@")[0] == "oni":
        print("yes"); raise SystemExit
print("no")
PY
)

# --- skills reachable -------------------------------------------------------
echo "skills"
expected=$(find "$PACK/skills" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
for harness in claude codex; do
  dir="$HOME/.$harness/skills"
  if [[ ! -d "$dir" ]]; then
    printf '  --    %s not installed on this machine\n' "$harness"
    continue
  fi
  linked=0
  for link in "$dir"/*; do
    [[ -L "$link" ]] || continue
    dest="$(cd "$(dirname "$link")" && readlink "$link")"
    [[ "$dest" == "$PACK"/* ]] && linked=$((linked + 1))
  done
  if [[ "$linked" -eq 0 ]]; then
    if [[ "$harness" == "claude" && "$plugin_installed" == "yes" ]]; then
      ok "claude: installed as a plugin (no symlinks by design)"
    else
      warn "$harness: no oni skills linked"
      fix "./scripts/install.sh $harness   (or install as a plugin)"
    fi
  elif [[ "$linked" -lt "$expected" ]]; then
    warn "$harness: $linked of $expected skills linked"
    fix "./scripts/install.sh $harness"
  else
    ok "$harness: $linked/$expected skills linked"
  fi
done


# --- router hook ------------------------------------------------------------
echo
echo "router hook"
if [[ ! -f "$SETTINGS" ]]; then
  warn "no settings file at $SETTINGS"
elif ! json_ok "$SETTINGS"; then
  warn "$SETTINGS is not valid JSON — every setting in it is being ignored"
  fix "repair the JSON, then re-run"
else
  cmd=$(python3 - "$SETTINGS" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
for entry in s.get("hooks", {}).get("SessionStart", []):
    for h in entry.get("hooks", []):
        c = h.get("command", "")
        if "oni-router.sh" in c:
            print(c)
PY
)
  if [[ -z "$cmd" ]]; then
    if [[ "$plugin_installed" == "yes" ]]; then
      ok "no settings hook, but the plugin install wires its own"
    else
      warn "router hook not configured — skills load but gates will not fire"
      fix "./scripts/install-hook.sh"
    fi
  else
    target=$(last_arg "$cmd")
    if [[ -f "$target" ]]; then
      ok "hook configured and its script exists"
    else
      warn "hook points at a script that does not exist: $target"
      fix "./scripts/install-hook.sh   (rewrites it for this checkout)"
    fi
  fi
fi

# --- codex router -----------------------------------------------------------
AGENTS="${CODEX_AGENTS:-$HOME/.codex/AGENTS.md}"
if [[ -d "$HOME/.codex" ]]; then
  echo
  echo "codex router"
  if [[ ! -f "$AGENTS" ]]; then
    warn "no $AGENTS — skills load but nothing routes to them"
    fix "./scripts/install-hook-codex.sh"
  elif ! grep -q "oni-router.md" "$AGENTS"; then
    warn "AGENTS.md has no oni import — skills load but gates will not fire"
    fix "./scripts/install-hook-codex.sh"
  else
    # The import is a whole line, "@<path>", and the path may contain spaces.
    imported=$(sed -n 's/^[[:space:]]*@\(\/.*oni-router\.md\)[[:space:]]*$/\1/p' "$AGENTS" | head -1)
    if [[ -f "$imported" ]]; then
      ok "AGENTS.md imports the router and the file exists"
    else
      warn "AGENTS.md imports a router that does not exist: $imported"
      fix "./scripts/install-hook-codex.sh   (rewrites it for this checkout)"
    fi
  fi
fi

# --- competing packs --------------------------------------------------------
echo
echo "overlap"
if [[ -f "$SETTINGS" ]]; then
  others=$(python3 - "$SETTINGS" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
names = [k for k, v in s.get("enabledPlugins", {}).items() if v and "superpowers" in k]
print(" ".join(names))
PY
)
  if [[ -n "$others" ]]; then
    warn "superpowers is also enabled: $others"
    fix "/plugin disable superpowers   — you pay both packs' descriptions every session"
  else
    ok "no competing process pack enabled"
  fi
fi

# --- baseline ---------------------------------------------------------------
echo
echo "oni-tune baseline"
local_bl="$PACK/scripts/baseline.local.json"
shared_bl="$PACK/scripts/baseline.json"
if [[ -f "$local_bl" ]]; then
  roots=$(baseline_roots "$local_bl")
  shown=${roots//$'\n'/, }
  ok "machine-local baseline present (${shown:-no roots recorded})"
elif [[ -f "$shared_bl" ]]; then
  roots=$(baseline_roots "$shared_bl")
  missing=0
  [[ -z "$roots" ]] && missing=1   # the committed baseline is the author's and records no roots
  while IFS= read -r r; do
    [[ -z "$r" || -e "$r" ]] || missing=1
  done <<< "$roots"
  if [[ "$missing" -eq 1 ]]; then
    warn "only the committed baseline exists; it holds the author's counts, not yours"
    fix "python3 scripts/scan.py --roots <your repos> --write-baseline"
  else
    ok "committed baseline's roots exist here"
  fi
else
  warn "no baseline — oni-tune cannot report drift"
  fix "python3 scripts/scan.py --roots <your repos> --write-baseline"
fi

echo
if [[ "$problems" -eq 0 ]]; then
  echo "All good."
else
  echo "$problems thing(s) to fix above."
fi
exit 0
