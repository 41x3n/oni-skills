#!/usr/bin/env python3
"""Count the code patterns that back the oni language rules.

Each entry in PATTERNS is the evidence for one rule in skills/oni-*/SKILL.md.
The committed baseline.json holds counts mined from the author's private
production repos; it records no roots and cannot be re-run elsewhere. Build
your own baseline first, then compare later scans against it.
Source symlinks, special files, and files larger than 2 MiB are skipped.

    python3 scripts/scan.py --roots ~/src/your-repos
    python3 scripts/scan.py --roots ~/src/your-repos --write-baseline
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
from collections import Counter
from pathlib import Path

SKIP_DIRS = {
    "node_modules", "vendor", ".venv", "venv", "dist", "build",
    ".git", "__pycache__", ".next", ".turbo", "coverage",
}

EXT_LANG = {".go": "go", ".py": "py", ".ts": "ts", ".tsx": "ts"}
MAX_SOURCE_BYTES = 2 * 1024 * 1024

# (rule_key, regex, direction)
#   direction "bad"  -> a rule fires while the count is above zero
#   direction "good" -> a practice we want to stay high
# Every pattern must run in linear time: scans read untrusted files up to 2 MiB.
# `[^\S\n]` is whitespace without newline; `(?:(?!tok)X)*` stops a scan at the
# next start token so repeated starts cannot rescan the same text.
PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "go": [
        ("bare_go_func", r"\bgo func\(", "bad"),
        ("errgroup_or_waitgroup", r"errgroup|sync\.WaitGroup", "good"),
        ("ignored_error", r"^[^\S\n]*_ = ", "bad"),
        ("errorf_pct_v", r"fmt\.Errorf\((?:(?!fmt\.Errorf\()[^)])*%v[^)]*", "bad"),
        ("errorf_pct_w", r"fmt\.Errorf\((?:(?!fmt\.Errorf\()[^)])*%w[^)]*", "good"),
        ("bare_any", r"\bany\b", "bad"),
        ("ctx_first_param", r"func (?:(?!func )[\w()*\s])*\(\s*ctx context\.Context", "good"),
        ("slog", r"\bslog\.", "good"),
        ("stdlib_log", r"\blog\.(Printf|Println|Fatal|Print)\b", "bad"),
        ("defer_close", r"defer \w+\.Close\(\)", "good"),
        ("panic", r"\bpanic\(", "bad"),
    ],
    "py": [
        ("blocking_sleep", r"\btime\.sleep\b", "bad"),
        ("async_def", r"\basync def\b", "good"),
        ("sync_requests", r"\brequests\.(get|post|put|delete)\b", "bad"),
        ("async_http", r"\bhttpx\b|\baiohttp\b", "good"),
        ("broad_except", r"except Exception", "bad"),
        ("except_pass", r"except(?:(?!except)[^\n])*:[^\S\n]*\n\s*pass", "bad"),
        ("dict_str_any", r"[Dd]ict\[str,\s*Any\]", "bad"),
        ("basemodel", r"\bBaseModel\b", "good"),
        ("print_call", r"^[^\S\n]*print\(", "bad"),
        ("logger", r"\blogger\.|\blogging\.", "good"),
    ],
    "ts": [
        ("double_cast", r"as unknown as", "bad"),
        ("real_cast", r"\bas (?!const\b)[A-Z]\w+", "bad"),
        ("as_const", r"\bas const\b", "good"),
        ("any_annotation", r":\s*any\b", "bad"),
        ("unknown_annotation", r":\s*unknown\b", "good"),
        ("non_null_assert", r"\w!\.", "bad"),
        ("floating_then", r"^[^\S\n]*[a-zA-Z_$][\w.]*\("
         r"(?:(?!\n[^\S\n]*[a-zA-Z_$][\w.]*\()[^)])*\)\.then", "bad"),
        ("zod", r"\bz\.[a-z]|from \"zod\"", "good"),
        ("console_log", r"\bconsole\.log\b", "bad"),
        ("loose_eq", r"[^=!<>]==[^=]", "bad"),
        ("ts_ignore", r"@ts-(ignore|expect-error)", "bad"),
        ("optional_chain", r"\?\.", "good"),
    ],
}

# Rules whose evidence needs per-file logic rather than a flat regex count.
def _py_untyped_params(src: str) -> int:
    n = 0
    # No match can end after the last ")"; cutting there keeps scans linear.
    for _name, params in re.findall(r"def (\w+)\(([^)]*)\)", src[:src.rfind(")") + 1]):
        parts = [p.strip() for p in params.split(",") if p.strip()]
        parts = [p for p in parts if p not in ("self", "cls") and not p.startswith("*")]
        if any(":" not in p for p in parts):
            n += 1
    return n


class _NextAt:
    """Cache "next match at or after pos". Callers move forward, so work stays linear."""

    def __init__(self, find) -> None:
        self.find, self.start, self.hit = find, -1, -1

    def __call__(self, pos: int) -> int:
        if pos < self.start or self.start < 0 or 0 <= self.hit < pos:
            self.start, self.hit = pos, self.find(pos)
        return self.hit


_IO_START = re.compile(r"func \w+\((?!ctx)")
_IO_CALL = re.compile(r"http\.|sql\.|\.Query|\.Exec")


def _go_io_without_ctx(src: str) -> int:
    r"""Count re.findall(r"func \w+\((?!ctx)[^)]*\)[^{]*\{[^}]*?(?:http\.|sql\.|\.Query|\.Exec)")
    without its quadratic rescans of the same body from every start."""
    def finder(ch: str) -> _NextAt:
        return _NextAt(lambda pos: src.find(ch, pos))

    paren, brace, close = finder(")"), finder("{"), finder("}")
    def next_call(pos: int) -> int:
        found = _IO_CALL.search(src, pos)
        return found.start() if found else -1

    call = _NextAt(next_call)
    n, pos = 0, 0
    while True:
        start = _IO_START.search(src, pos)
        if start is None:
            return n
        params_end = paren(start.end())
        body = brace(params_end + 1) if params_end >= 0 else -1
        if body < 0:
            return n  # no later start can find a ")" then "{" either
        body_end = close(body + 1)
        hit = call(body + 1)
        if hit >= 0 and (body_end < 0 or hit < body_end):
            n += 1
            pos = _IO_CALL.match(src, hit).end()
        else:
            pos = start.start() + 1


CUSTOM = {
    "py": [("untyped_params", _py_untyped_params, "bad")],
    "go": [("io_without_ctx", _go_io_without_ctx, "bad")],
}


def is_test(path: str, lang: str) -> bool:
    base = os.path.basename(path)
    if lang == "go":
        return base.endswith("_test.go")
    if lang == "py":
        return base.startswith("test_") or base.endswith("_test.py") or "/tests/" in path
    return ".test." in base or ".spec." in base


def read_source(root_fd: int, parts: tuple[str, ...]) -> str | None:
    """Read a bounded regular file beneath an already-open source directory."""
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    directory_fd = os.dup(root_fd)
    try:
        # Open each parent relative to the previous descriptor. A symlink swap
        # cannot redirect the leaf read outside the selected directory tree.
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        source_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                            dir_fd=directory_fd)
        with os.fdopen(source_fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
                return None
            # Bound the read even if the file grows after fstat.
            data = source.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                return None
            return data.decode("utf-8", errors="ignore")
    except OSError:
        return None  # Unreadable, removed, or replaced source files are skipped.
    finally:
        os.close(directory_fd)


def scan(roots: list[Path]) -> dict[str, dict[str, int]]:
    compiled = {
        lang: [(key, re.compile(rx, re.M), d) for key, rx, d in pats]
        for lang, pats in PATTERNS.items()
    }
    counts: dict[str, Counter] = {lang: Counter() for lang in PATTERNS}
    files: Counter = Counter()

    for root in roots:
        try:
            root = root.resolve(strict=True)
            root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for name in filenames:
                    lang = EXT_LANG.get(os.path.splitext(name)[1])
                    if not lang:
                        continue
                    path = Path(dirpath) / name
                    src = read_source(root_fd, path.relative_to(root).parts)
                    if src is None:
                        continue
                    files[lang] += 1
                    testfile = is_test(str(path), lang)
                    if not testfile:  # test files legitimately differ
                        files[f"{lang}_src"] += 1
                    for key, rx, _d in compiled[lang]:
                        counts[lang][key] += len(rx.findall(src))
                    for key, fn, _d in CUSTOM.get(lang, []):
                        if not testfile:
                            counts[lang][key] += fn(src)
        finally:
            os.close(root_fd)

    out: dict[str, dict[str, int]] = {}
    for lang in PATTERNS:
        out[lang] = dict(sorted(counts[lang].items()))
        out[lang]["_files"] = files[lang]
        out[lang]["_files_src"] = files[f"{lang}_src"]
    return out


def direction(lang: str, key: str) -> str:
    for k, _rx, d in PATTERNS.get(lang, []):
        if k == key:
            return d
    for k, _fn, d in CUSTOM.get(lang, []):
        if k == key:
            return d
    return "bad"


def report(now: dict, base: dict | None) -> int:
    drift = 0
    for lang in ("go", "py", "ts"):
        cur = now.get(lang, {})
        old = (base or {}).get(lang, {})
        print(f"\n### {lang}  ({cur.get('_files_src', 0)} source files, {cur.get('_files', 0)} total)")
        print(f"{'pattern':26s} {'was':>7} {'now':>7} {'delta':>7}  verdict")
        for key in sorted(k for k in cur if not k.startswith("_")):
            n = cur[key]
            b = old.get(key)
            d = "" if b is None else f"{n - b:+d}"
            dirn = direction(lang, key)
            if b is None:
                verdict = "new"
            elif dirn == "bad" and n == 0 and b > 0:
                verdict = "RULE NO LONGER FIRES - propose cut"
                drift += 1
            elif dirn == "bad" and n > b * 1.5 and n - b > 5:
                verdict = "getting worse - keep rule"
                drift += 1
            elif dirn == "good" and b > 0 and n < b * 0.5:
                verdict = "GOOD PRACTICE DECLINING"
                drift += 1
            else:
                verdict = "stable"
            print(f"{key:26s} {('-' if b is None else b):>7} {n:>7} {d:>7}  {verdict}")
    return drift


HERE = Path(__file__).parent
SHARED_BASELINE = HERE / "baseline.json"        # committed; the machine it was mined on
LOCAL_BASELINE = HERE / "baseline.local.json"   # gitignored; this machine


def default_baseline(for_write: bool) -> Path:
    """Writes always go to the machine-local file so two machines never conflict.
    Reads prefer the local file and fall back to the committed one."""
    if for_write:
        return LOCAL_BASELINE
    return LOCAL_BASELINE if LOCAL_BASELINE.exists() else SHARED_BASELINE


def resolve_roots(flag: list[Path] | None, base: dict | None) -> list[Path]:
    """--roots, else $ONI_SCAN_ROOTS, else whatever the baseline was built from."""
    if flag:
        return [p.expanduser() for p in flag]
    env = os.environ.get("ONI_SCAN_ROOTS", "").strip()
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p]
    if base and base.get("_roots"):
        return [Path(p).expanduser() for p in base["_roots"]]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", type=Path,
                    help="repos to scan; defaults to $ONI_SCAN_ROOTS, else the baseline's roots")
    ap.add_argument("--baseline", type=Path, help="baseline file (default: baseline.local.json)")
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit raw counts and exit")
    args = ap.parse_args()

    read_path = args.baseline or default_baseline(for_write=False)
    base = json.loads(read_path.read_text()) if read_path.exists() else None

    roots = resolve_roots(args.roots, base)
    if not roots:
        print("No roots to scan. The committed baseline.json holds counts from the author's\n"
              "private repos and records no paths, so there is nothing to re-scan here.\n"
              "Build a baseline from repos you have, then re-run without --roots:\n"
              f"  python3 {sys.argv[0]} --roots ~/path/to/repos --write-baseline\n"
              "(or pass --roots, or set ONI_SCAN_ROOTS)", file=sys.stderr)
        return 2
    missing = [p for p in roots if not p.exists()]
    if missing:
        print(f"no such path: {', '.join(map(str, missing))}", file=sys.stderr)
        return 2

    now = scan(roots)
    now["_roots"] = [str(p) for p in roots]
    now["_generated"] = time.strftime("%Y-%m-%d")

    if args.json:
        json.dump(now, sys.stdout, indent=2)
        print()
        return 0

    if args.write_baseline:
        write_path = args.baseline or default_baseline(for_write=True)
        write_path.write_text(json.dumps(now, indent=2) + "\n")
        print(f"baseline written: {write_path}")
        print(f"  roots: {', '.join(now['_roots'])}")
        return 0

    if base is None:
        print(f"No baseline at {read_path}. Counts below are current state, not drift.\n"
              f"Write one first:  python3 {sys.argv[0]} --roots <repos> --write-baseline\n")
    else:
        base_roots = base.get("_roots")
        if not base_roots:
            print(f"WARNING: baseline {read_path.name} records no roots. The committed one holds\n"
                  f"counts from the author's repos, not yours, so every verdict below is\n"
                  f"meaningless until you write your own:\n"
                  f"  python3 {sys.argv[0]} --roots {' '.join(str(p) for p in roots)} --write-baseline\n")
        elif set(base_roots) != {str(p) for p in roots}:
            # Comparing this machine's code against another machine's counts
            # produces drift verdicts that are pure noise.
            print(f"WARNING: baseline {read_path.name} was built from:\n"
                  f"  {', '.join(base_roots)}\n"
                  f"but you are scanning:\n"
                  f"  {', '.join(str(p) for p in roots)}\n"
                  f"Every verdict below is meaningless until you re-baseline:\n"
                  f"  python3 scripts/scan.py --write-baseline\n")

    drift = report(now, base)
    print(f"\n{drift} pattern(s) drifted." if drift else "\nno drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
