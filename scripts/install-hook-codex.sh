#!/usr/bin/env bash
# Wire the oni routing table into Codex.
#
# Codex has no plugin system and no SessionStart hook. Its global instruction
# file is ~/.codex/AGENTS.md, which supports `@path` imports — so the router
# goes in as an import line pointing at this checkout.
#
#   ./scripts/install-hook-codex.sh            add or update
#   ./scripts/install-hook-codex.sh --remove   take it back out
#   DRY_RUN=1 ./scripts/install-hook-codex.sh  show the result, write nothing
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
AGENTS="${CODEX_AGENTS:-$HOME/.codex/AGENTS.md}"
ROUTER="$PACK/hooks/oni-router.md"
MODE="${1:-add}"

[[ -f "$ROUTER" ]] || { echo "no router at $ROUTER" >&2; exit 2; }
# The import is one line; a line break in the path would split it.
if [[ "$PACK" == *$'\n'* || "$PACK" == *$'\r'* ]]; then
  echo "checkout path contains a line break; move the checkout and re-run: $PACK" >&2
  exit 2
fi

if [[ ! -f "$AGENTS" ]]; then
  if [[ "$MODE" == "--remove" ]]; then
    echo "no $AGENTS — nothing to remove"
    exit 0
  fi
  if [[ -z "${DRY_RUN:-}" ]]; then   # a dry run writes nothing, not even the file
    mkdir -p "$(dirname "$AGENTS")"
    : > "$AGENTS"
    echo "created $AGENTS"
  fi
fi

# Mark new imports so a moved checkout can be updated without guessing ownership.
# An unmarked legacy import belongs to us only at this checkout's exact path.
python3 - "$AGENTS" "$ROUTER" "$MODE" "${DRY_RUN:-}" <<'PY'
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath

agents_path, router, mode, dry = sys.argv[1:5]
agents = Path(agents_path)
try:
    original = agents.read_text()
except FileNotFoundError:             # dry run against a file not yet created
    original = ""
marker = "<!-- oni:router-import -->"

def is_oni_import(line: str) -> bool:
    line = line.strip()
    if not line.startswith("@/"):
        return False
    path = PurePosixPath(line[1:])
    return path.name == "oni-router.md" and path.parent.name == "hooks"

lines = original.splitlines(keepends=True)
kept, index, unknown = [], 0, 0
while index < len(lines):
    line = lines[index]
    if (line.strip() == marker and index + 1 < len(lines)
            and is_oni_import(lines[index + 1])):
        index += 2
        continue
    if is_oni_import(line):
        if PurePosixPath(line.strip()[1:]) == PurePosixPath(router):
            index += 1
            continue
        unknown += 1
    kept.append(line)
    index += 1
filtered = "".join(kept)
removed = filtered != original
if mode == "--remove":
    result = filtered
    action = "removed the oni import" if removed else "nothing to remove"
else:
    prefix = filtered.rstrip("\r\n")
    result = (prefix + "\n\n" if prefix else "") + f"{marker}\n@{router}\n"
    action = "updated the oni import" if removed else "added the oni import"

if unknown:
    print("Kept unmarked router imports at other paths. Review stale Oni imports manually.")

if dry:
    print(f"[dry run] would have {action}\n---")
    print(result, end="")
    sys.exit(0)

if result == original:
    print(f"oni import already up to date in {agents_path}; nothing written.")
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

backup = write_atomically(agents_path, result)
print(f"{action}: @{router}")
print(f"backup: {backup}")
print("Takes effect in your next Codex session.")
PY
