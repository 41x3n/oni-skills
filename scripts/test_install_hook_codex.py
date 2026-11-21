"""Check import ownership without touching the user's Codex configuration."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/install-hook-codex.sh"


class CodexInstallerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.agents = self.folder / "AGENTS.md"
        self.unrelated = (
            "Never disclose secrets when reviewing oni-router.md.\n"
            "# @/former checkout/hooks/oni-router.md\n"
            "Read @/former checkout/hooks/oni-router.md before review.\n"
            "@/docs/oni-router.md\n"
            "@/docs/hooks/oni-router.md.example\n"
            "@/docs/other.md\n"
            "@/other-tool/hooks/oni-router.md\n"
        )
        self.original = self.unrelated + "<!-- oni:router-import -->\n@/former checkout/hooks/oni-router.md\n"
        self.agents.write_text(self.original)
        self.agents.chmod(0o600)
        self.env = dict(os.environ, CODEX_AGENTS=str(self.agents))
        self.env.pop("DRY_RUN", None)

    def run_installer(self, *args: str) -> None:
        subprocess.run(["bash", str(SCRIPT), *args], env=self.env, cwd=self.folder,
                       capture_output=True, text=True, check=True, timeout=15)

    def assert_preserved(self) -> None:
        result = self.agents.read_text()
        for line in self.unrelated.splitlines():
            self.assertIn(line + "\n", result)
        self.assertNotIn("\n@/former checkout/hooks/oni-router.md\n", result)
        self.assertEqual(self.agents.stat().st_mode & 0o777, 0o600)

    def test_add_preserves_prose_and_unrelated_imports_and_is_idempotent(self) -> None:
        self.run_installer()
        self.assert_preserved()
        first = self.agents.read_text()
        self.assertEqual(first.splitlines().count(f"@{ROOT}/hooks/oni-router.md"), 1)
        backup = next(self.folder.glob("AGENTS.md.pre-oni-*"))
        self.assertEqual(backup.read_text(), self.original)
        self.run_installer()
        self.assertEqual(self.agents.read_text(), first)

    def test_unchanged_file_writes_no_backup(self) -> None:
        self.run_installer()
        for backup in self.folder.glob("AGENTS.md.pre-oni-*"):
            backup.unlink()
        self.run_installer()
        self.assertEqual(list(self.folder.glob("AGENTS.md.pre-oni-*")), [])

    def test_remove_preserves_prose_and_unrelated_imports(self) -> None:
        self.run_installer("--remove")
        self.assert_preserved()
        self.assertEqual(self.agents.read_text(), self.unrelated)
        first = self.agents.read_text()
        self.run_installer("--remove")
        self.assertEqual(self.agents.read_text(), first)

    def test_current_unmarked_legacy_import_is_upgraded(self) -> None:
        self.agents.write_text(self.unrelated + f"@{ROOT}/hooks/oni-router.md\n")
        self.run_installer()
        self.assert_preserved()
        self.assertEqual(self.agents.read_text().splitlines().count(f"@{ROOT}/hooks/oni-router.md"), 1)
        self.assertIn("<!-- oni:router-import -->\n", self.agents.read_text())


    def test_dry_run_creates_nothing(self) -> None:
        home = self.folder / "home"
        env = dict(self.env, DRY_RUN="1", CODEX_AGENTS=str(home / ".codex/AGENTS.md"))
        result = subprocess.run(["bash", str(SCRIPT)], env=env, cwd=self.folder,
                                capture_output=True, text=True, check=True, timeout=15)
        self.assertIn("[dry run] would have added the oni import", result.stdout)
        self.assertFalse(home.exists())

    def test_backups_are_private_and_capped(self) -> None:
        legacy = self.folder / "AGENTS.md.pre-oni-20000101000000"
        foreign = self.folder / "AGENTS.md.pre-oni-notes"
        legacy.write_text("old")
        foreign.write_text("keep")
        for run in range(7):
            self.run_installer("--remove" if run % 2 else "add")
        backups = sorted(self.folder.glob("AGENTS.md.pre-oni-2*"))
        self.assertEqual(len(backups), 5)
        self.assertNotIn(legacy, backups)
        self.assertEqual(foreign.read_text(), "keep")
        for backup in backups:
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_symlinked_file_stays_linked(self) -> None:
        real = self.folder / "dotfiles" / "AGENTS.md"
        real.parent.mkdir()
        self.agents.rename(real)
        self.agents.symlink_to(real)
        self.run_installer()
        self.assert_preserved()
        self.assertTrue(self.agents.is_symlink())

    def test_checkout_path_with_line_break_is_refused(self) -> None:
        pack = self.folder / "pack\rline"
        (pack / "scripts").mkdir(parents=True)
        (pack / "hooks").mkdir()
        shutil.copy2(SCRIPT, pack / "scripts/install-hook-codex.sh")
        (pack / "hooks/oni-router.md").write_text("# router\n")
        result = subprocess.run(["bash", str(pack / "scripts/install-hook-codex.sh")], env=self.env,
                                cwd=self.folder, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn("line break", result.stderr)
        self.assertEqual(self.agents.read_text(), self.original)

    def test_doctor_reads_import_and_baseline_roots_with_spaces(self) -> None:
        pack = self.folder / "pack with space"
        (pack / "scripts").mkdir(parents=True)
        (pack / "hooks").mkdir()
        (pack / "skills").mkdir()
        shutil.copy2(ROOT / "scripts/doctor.sh", pack / "scripts/doctor.sh")
        (pack / "hooks/oni-router.md").write_text("# router\n")
        root = self.folder / "repos, mine"
        root.mkdir()
        (pack / "scripts/baseline.json").write_text(json.dumps({"_roots": [str(root)]}))
        (self.folder / "home/.codex").mkdir(parents=True)
        self.agents.write_text(f"<!-- oni:router-import -->\n@{pack}/hooks/oni-router.md\n")
        env = dict(self.env, HOME=str(self.folder / "home"),
                   CLAUDE_SETTINGS=str(self.folder / "missing.json"))
        result = subprocess.run(["bash", str(pack / "scripts/doctor.sh")], env=env, cwd=self.folder,
                                capture_output=True, text=True, check=True, timeout=30)
        self.assertIn("AGENTS.md imports the router and the file exists", result.stdout)
        self.assertIn("committed baseline's roots exist here", result.stdout)

if __name__ == "__main__":
    unittest.main()
