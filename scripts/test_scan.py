"""Exercise source reads with hostile files in temporary directories."""

import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import scan


ROOT = Path(__file__).resolve().parents[1]


class SourceScannerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.root = self.folder / "source"
        self.root.mkdir()
        self.outside = self.folder / "outside"
        self.outside.mkdir()
        (self.outside / "secret.py").write_text("time.sleep(1)\n")

    def test_regular_sources_and_tests_still_count(self) -> None:
        (self.root / "source.py").write_text("async def run():\n    time.sleep(1)\n")
        (self.root / "test_source.py").write_text("def test_run():\n    pass\n")
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "source.ts").write_text("const value = source?.value\n")
        result = scan.scan([self.root])
        self.assertEqual(result["py"]["_files"], 2)
        self.assertEqual(result["py"]["_files_src"], 1)
        self.assertEqual(result["py"]["blocking_sleep"], 1)
        self.assertEqual(result["ts"]["optional_chain"], 1)

    def test_source_and_directory_links_are_not_followed(self) -> None:
        (self.root / "regular.py").write_text("pass\n")
        (self.root / "external.py").symlink_to(self.outside / "secret.py")
        (self.root / "internal.py").symlink_to(self.root / "regular.py")
        (self.root / "external-directory").symlink_to(self.outside, target_is_directory=True)
        result = scan.scan([self.root])
        self.assertEqual(result["py"]["_files"], 1)
        self.assertEqual(result["py"].get("blocking_sleep", 0), 0)

    def test_fifo_and_fifo_link_do_not_block(self) -> None:
        pipe = self.root / "pipe.py"
        os.mkfifo(pipe)
        (self.root / "linked.py").symlink_to(pipe)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/scan.py"), "--roots", str(self.root),
             "--baseline", str(self.folder / "missing.json"), "--json"],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True, text=True, check=True, timeout=2,
        )
        self.assertEqual(json.loads(result.stdout)["py"]["_files"], 0)

    def test_oversized_source_is_skipped_instead_of_partially_counted(self) -> None:
        with (self.root / "huge.py").open("wb") as source:
            source.write(b"time.sleep(1)\n")
            source.truncate(2 * 1024 * 1024 + 1)
        result = scan.scan([self.root])
        self.assertEqual(result["py"]["_files"], 0)

    def test_leaf_replaced_by_link_before_open_is_rejected(self) -> None:
        source = self.root / "replace.py"
        source.write_text("pass\n")
        real_open = os.open

        def replace_then_open(path: str, flags: int, *args, **kwargs) -> int:
            if path == "replace.py":
                source.unlink()
                source.symlink_to(self.outside / "secret.py")
            return real_open(path, flags, *args, **kwargs)

        with patch("scripts.scan.os.open", side_effect=replace_then_open):
            result = scan.scan([self.root])
        self.assertEqual(result["py"]["_files"], 0)

    def test_source_growing_after_stat_is_not_partially_counted(self) -> None:
        source = self.root / "growing.py"
        source.write_text("time.sleep(1)\n")
        real_fstat = os.fstat

        def grow_after_stat(fd: int) -> os.stat_result:
            info = real_fstat(fd)
            with source.open("ab") as writer:
                writer.truncate(scan.MAX_SOURCE_BYTES + 1)
            return info

        with patch("scripts.scan.os.fstat", side_effect=grow_after_stat):
            result = scan.scan([self.root])
        self.assertEqual(result["py"]["_files"], 0)

    def test_parent_replaced_by_link_before_open_cannot_escape_root(self) -> None:
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "secret.py").write_text("pass\n")
        real_open = os.open

        def replace_then_open(path: str, flags: int, *args, **kwargs) -> int:
            if path == "nested":
                nested.rename(self.root / "preserved-directory")
                nested.symlink_to(self.outside, target_is_directory=True)
            return real_open(path, flags, *args, **kwargs)

        with patch("scripts.scan.os.open", side_effect=replace_then_open):
            result = scan.scan([self.root])
        self.assertEqual(result["py"]["_files"], 0)
        self.assertEqual(result["py"].get("blocking_sleep", 0), 0)


# The pre-linear forms. Each was quadratic on repeated start tokens; the
# rewrites must still return the same counts.
LEGACY = {
    "ignored_error": r"^\s*_ = ",
    "errorf_pct_v": r"fmt\.Errorf\([^)]*%v",
    "errorf_pct_w": r"fmt\.Errorf\([^)]*%w",
    "ctx_first_param": r"func [\w()*\s]*\(\s*ctx context\.Context",
    "except_pass": r"except[^\n]*:\s*\n\s*pass",
    "print_call": r"^\s*print\(",
    "floating_then": r"^\s*[a-zA-Z_$][\w.]*\([^)]*\)\.then",
    "io_without_ctx": r"func \w+\((?!ctx)[^)]*\)[^{]*\{[^}]*?(?:http\.|sql\.|\.Query|\.Exec)",
    "untyped_params": r"def (\w+)\(([^)]*)\)",
}
PIECES = ["except", "except:", "exception", ":", " ", "\t", "\n", "\r", "pass", "x", "(", ")",
          "{", "}", "func ", "func a(", "fmt.Errorf(", "%v", "%w", ",", "ctx context.Context",
          ".", "*", "_ = ", "print(", "a(", ").then", "foo.bar(", "http.", ".Query", "def f(",
          "a: int", "self", "\x0b"]


class PatternCostTest(unittest.TestCase):
    def counters(self) -> dict:
        found = {key: (lambda src, rx=re.compile(rx, re.M): len(rx.findall(src)))
                 for pats in scan.PATTERNS.values() for key, rx, _d in pats}
        found.update({key: fn for fns in scan.CUSTOM.values() for key, fn, _d in fns})
        return found

    def test_counts_match_legacy_patterns(self) -> None:
        counters = self.counters()
        rng = random.Random(7)
        for _ in range(3000):
            src = "".join(rng.choice(PIECES) for _ in range(rng.randint(0, 40)))
            for key, rx in LEGACY.items():
                if key == "untyped_params":  # same matches feed the same param check
                    real = re.findall
                    with patch("scripts.scan.re.findall", lambda _rx, _src: real(rx, src)):
                        want = scan._py_untyped_params(src)
                else:
                    want = len(re.findall(rx, src, re.M))
                self.assertEqual(counters[key](src), want, (key, src))

    def test_adversarial_sources_scan_in_linear_time(self) -> None:
        counters = self.counters()
        tokens = ["except:", "\n", "func ", "func a() {", "fmt.Errorf(", "def a(", "a(\n", "pass"]
        for token in tokens:
            src = token * (500_000 // len(token))
            started = time.perf_counter()
            for count in counters.values():
                count(src)
            self.assertLess(time.perf_counter() - started, 2, repr(token))


if __name__ == "__main__":
    unittest.main()
