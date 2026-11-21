#!/usr/bin/env bash
# Add (or update) the oni SessionStart router hook in ~/.claude/settings.json,
# using this checkout's absolute path. Idempotent; backs up before writing.
#
#   ./scripts/install-hook.sh            add or update
#   ./scripts/install-hook.sh --remove   take it back out
#   DRY_RUN=1 ./scripts/install-hook.sh  print the result, write nothing
#
# Only needed for a symlink install. Installing oni as a plugin wires the hook
# through plugin.json and this script is unnecessary.
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
ROUTER="$PACK/hooks/oni-router.sh"
MODE="${1:-add}"

[[ -f "$ROUTER" ]] || { echo "no router script at $ROUTER" >&2; exit 2; }
if [[ "$PACK" == *$'\n'* || "$PACK" == *$'\r'* ]]; then
  echo "checkout path contains a line break; move the checkout and re-run: $PACK" >&2
  exit 2
fi
if [[ ! -f "$SETTINGS" ]]; then
  if [[ "$MODE" == "--remove" ]]; then
    echo "no $SETTINGS — nothing to remove"
    exit 0
  fi
  if [[ ! -d "$(dirname "$SETTINGS")" ]]; then
    echo "$(dirname "$SETTINGS") does not exist. Install and run Claude Code once, then re-run this script." >&2
    exit 1
  fi
  if [[ -z "${DRY_RUN:-}" ]]; then
    echo '{}' > "$SETTINGS"
    echo "created $SETTINGS (it did not exist)"
  fi
fi

python3 - "$SETTINGS" "$ROUTER" "$MODE" "${DRY_RUN:-}" <<'PY'
import json, os, re, shlex, stat, sys, tempfile, time
from pathlib import PurePosixPath
settings_path, router, mode, dry = sys.argv[1:5]
# shlex.quote or a checkout path containing a space, $(...), or a backtick
# becomes shell injection that runs on every session start.
command = f"bash {shlex.quote(router)}"

try:
    with open(settings_path) as fh:
        original = fh.read()
except FileNotFoundError:             # dry run against a settings file not yet created
    original = "{}"

def unique_keys(pairs: list) -> dict:
    # json keeps the last duplicate silently; rewriting would drop the others.
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen[key] = value
    return seen

try:
    settings = json.loads(original, object_pairs_hook=unique_keys)
except ValueError as err:              # never rewrite a file we could not read faithfully
    sys.exit(f"{settings_path}: {err}. Fix it by hand and re-run; nothing was written.")

hooks = settings.setdefault("hooks", {})
entries = hooks.get("SessionStart", [])

def is_oni_hook(h: dict) -> bool:
    command = h.get("command")
    if h.get("type") != "command" or not isinstance(command, str):
        return False
    # Recognize only the two-argument command we install. Shell operators and
    # unquoted newlines are separate tokens, not part of an owned invocation.
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        args = list(lexer)
    except ValueError:  # A malformed foreign command is not ours to delete.
        return False
    if len(args) != 2 or args[0] not in {"bash", "/bin/bash", "/usr/bin/bash"}:
        return False
    path = PurePosixPath(args[1])
    if not (path.is_absolute() and path.name == "oni-router.sh" and path.parent.name == "hooks"):
        return False
    # Existing Oni installers emit this status message. It identifies moved
    # checkouts; an unmarked command is owned only at our exact current path.
    return path == PurePosixPath(router) or h.get("statusMessage") == "Loading oni routing table..."

# Strip only our own hooks. Dropping the whole entry would delete a user's
# hooks that happen to share the group.
kept, removed = [], 0
for entry in entries:
    inner = entry.get("hooks", [])
    survivors = [h for h in inner if not is_oni_hook(h)]
    removed += len(inner) - len(survivors)
    if survivors or not inner:
        kept.append({**entry, "hooks": survivors} if survivors else entry)

if mode == "--remove":
    if kept:
        hooks["SessionStart"] = kept
    else:
        hooks.pop("SessionStart", None)
    action = f"removed {removed} oni hook(s)" if removed else "nothing to remove"
else:
    kept.append({
        "hooks": [{
            "type": "command",
            "command": command,
            "timeout": 5,
            "statusMessage": "Loading oni routing table...",
        }]
    })
    hooks["SessionStart"] = kept
    action = "updated oni hook" if removed else "added oni hook"

rendered = json.dumps(settings, indent=2) + "\n"

if dry:
    print(f"[dry run] would have {action}\n")
    print(rendered)
    sys.exit(0)

if rendered == original:
    print(f"oni hook already up to date in {settings_path}; nothing written.")
    sys.exit(0)

def make_backup(path: str, data: bytes, mode: int) -> str:
    # Exclusive create: an existing backup is never overwritten. Created 0600,
    # then set to the original mode, so a private file is never exposed.
    stem = f"{path}.pre-oni-{time.strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
    for n in range(1000):
        name = f"{stem}-{n}" if n else stem
        try:
            fh = open(name, "xb", opener=lambda p, f: os.open(p, f, 0o600))
        except FileExistsError:
            continue
        with fh:
            os.fchmod(fh.fileno(), mode)
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        return name
    sys.exit(f"no free backup name beside {path}; nothing was written.")

def prune_backups(path: str, keep: int = 5) -> None:
    folder, base = os.path.split(os.path.abspath(path))
    own = re.compile(re.escape(base) + r"\.pre-oni-(\d{14})(?:-\d+){0,2}")
    found = []
    for name in os.listdir(folder):
        match = own.fullmatch(name)
        info = os.lstat(os.path.join(folder, name)) if match else None
        if info and stat.S_ISREG(info.st_mode):
            found.append((match.group(1), info.st_mtime_ns, name))
    for *_, name in sorted(found)[:-keep]:
        os.unlink(os.path.join(folder, name))

def write_atomically(path: str, text: str) -> str:
    target = os.path.realpath(path)   # a symlinked settings file stays a symlink
    mode = stat.S_IMODE(os.stat(target).st_mode)
    with open(target, "rb") as fh:
        backup = make_backup(path, fh.read(), mode)
    tmp = tempfile.NamedTemporaryFile("w", dir=os.path.dirname(target), delete=False,
                                      prefix=f".{os.path.basename(target)}.", suffix=".tmp")
    try:
        with tmp:
            tmp.write(text)
            tmp.flush()
            os.fchmod(tmp.fileno(), mode)
            os.fsync(tmp.fileno())
        os.replace(tmp.name, target)
    except BaseException:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise
    prune_backups(path)
    return backup

backup = write_atomically(settings_path, rendered)

print(f"{action}: {command}")
print(f"backup: {backup}")
print("Takes effect in your next session.")
PY
