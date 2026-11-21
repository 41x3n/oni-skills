"""Check hook ownership using temporary Claude settings."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ClaudeInstallerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.settings = self.folder / "settings.json"
        self.unrelated = [
            {"type": "command", "command": "python3 /opt/policy.py --audit-target oni-router.sh"},
            {"type": "command", "command": "bash /docs/oni-router.sh"},
            {"type": "command", "command": "bash /old/hooks/oni-router.sh; echo preserve"},
            {"type": "command", "command": "echo bash /old/hooks/oni-router.sh"},
            {"type": "command", "command": "bash\n/old/hooks/oni-router.sh"},
            {"type": "command", "command": "bash '/old/hooks/oni-router.sh"},
            {"type": "prompt", "command": "bash /old/hooks/oni-router.sh", "prompt": "Keep me"},
            {"type": "command", "command": "bash /other-tool/hooks/oni-router.sh"},
        ]
        owned = {"type": "command", "command": "bash '/former checkout/hooks/oni-router.sh'",
                 "statusMessage": "Loading oni routing table..."}
        self.original = {
            "permissions": {"deny": ["Read(.env)"]},
            "hooks": {"SessionStart": [{"matcher": "startup", "hooks": self.unrelated + [owned]}],
                      "Stop": [{"hooks": [{"type": "command", "command": "echo finished"}]}]},
        }
        self.settings.write_text(json.dumps(self.original))
        self.settings.chmod(0o600)
        self.env = dict(os.environ, CLAUDE_SETTINGS=str(self.settings))
        self.env.pop("DRY_RUN", None)

    def install(self, *args: str, script: Path | None = None) -> dict:
        subprocess.run(["bash", str(script or ROOT / "scripts/install-hook.sh"), *args],
                       env=self.env, cwd=self.folder, capture_output=True,
                       text=True, check=True, timeout=15)
        return json.loads(self.settings.read_text())

    def assert_preserved(self, config: dict) -> list[dict]:
        self.assertEqual(config["permissions"], self.original["permissions"])
        self.assertEqual(config["hooks"]["Stop"], self.original["hooks"]["Stop"])
        self.assertEqual(config["hooks"]["SessionStart"][0]["matcher"], "startup")
        hooks = [h for entry in config["hooks"]["SessionStart"] for h in entry["hooks"]]
        for hook in self.unrelated:
            self.assertIn(hook, hooks)
        self.assertEqual(self.settings.stat().st_mode & 0o777, 0o600)
        return hooks

    def test_add_preserves_foreign_hooks_and_replaces_former_checkout(self) -> None:
        config = self.install()
        hooks = self.assert_preserved(config)
        self.assertEqual(len(hooks), len(self.unrelated) + 1)
        self.assertIn({"type": "command", "command": f"bash {shlex.quote(str(ROOT / 'hooks/oni-router.sh'))}",
                       "timeout": 5, "statusMessage": "Loading oni routing table..."}, hooks)
        backup = next(self.folder.glob("settings.json.pre-oni-*"))
        self.assertEqual(json.loads(backup.read_text()), self.original)
        self.assertEqual(self.install(), config)

    def test_unchanged_settings_write_no_backup(self) -> None:
        config = self.install()
        for backup in self.folder.glob("settings.json.pre-oni-*"):
            backup.unlink()
        self.assertEqual(self.install(), config)
        self.assertEqual(list(self.folder.glob("settings.json.pre-oni-*")), [])

    def test_missing_settings_file_is_created(self) -> None:
        self.settings.unlink()
        config = self.install()
        hooks = [h for entry in config["hooks"]["SessionStart"] for h in entry["hooks"]]
        self.assertEqual([h["statusMessage"] for h in hooks], ["Loading oni routing table..."])

    def test_remove_preserves_foreign_hooks(self) -> None:
        config = self.install("--remove")
        self.assertEqual(self.assert_preserved(config), self.unrelated)
        self.assertEqual(self.install("--remove"), config)

    def test_current_unmarked_legacy_hook_is_removed(self) -> None:
        original = json.loads(self.settings.read_text())
        original["hooks"]["SessionStart"][0]["hooks"].append(
            {"type": "command", "command": f"bash {shlex.quote(str(ROOT / 'hooks/oni-router.sh'))}"})
        self.settings.write_text(json.dumps(original))
        self.assertEqual(self.assert_preserved(self.install("--remove")), self.unrelated)

    def test_hostile_checkout_path_remains_literal(self) -> None:
        pack = self.folder / "pack ' $(touch dollar) `touch backtick`"
        (pack / "scripts").mkdir(parents=True)
        (pack / "hooks").mkdir()
        shutil.copy2(ROOT / "scripts/install-hook.sh", pack / "scripts/install-hook.sh")
        (pack / "hooks/oni-router.sh").write_text("exit 0\n")
        config = self.install(script=pack / "scripts/install-hook.sh")
        command = config["hooks"]["SessionStart"][-1]["hooks"][0]["command"]
        subprocess.run(["/bin/sh", "-c", command], cwd=self.folder,
                       capture_output=True, check=True, timeout=5)
        self.assertFalse((self.folder / "dollar").exists())
        self.assertFalse((self.folder / "backtick").exists())
        self.install("--remove", script=pack / "scripts/install-hook.sh")
        self.assertEqual(self.assert_preserved(json.loads(self.settings.read_text())), self.unrelated)


    def test_duplicate_keys_abort_without_writing(self) -> None:
        text = '{"hooks": {}, "hooks": {"Stop": []}}'
        self.settings.write_text(text)
        result = subprocess.run(["bash", str(ROOT / "scripts/install-hook.sh")], env=self.env,
                                cwd=self.folder, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate key 'hooks'", result.stderr)
        self.assertEqual(self.settings.read_text(), text)
        self.assertEqual(list(self.folder.glob("settings.json.pre-oni-*")), [])

    def test_backups_are_private_never_overwritten_and_capped(self) -> None:
        legacy = self.folder / "settings.json.pre-oni-20000101000000"
        foreign = [self.folder / "settings.json.pre-oni-notes",
                   self.folder / "other.json.pre-oni-20000101000000"]
        for path in [legacy, *foreign]:
            path.write_text("keep?")
        states = []
        for run in range(7):
            states.append(self.settings.read_text())
            self.install("--remove" if run % 2 else "add")
        backups = sorted(self.folder.glob("settings.json.pre-oni-2*"))
        self.assertEqual(len(backups), 5)
        self.assertNotIn(legacy, backups)
        for path in foreign:
            self.assertEqual(path.read_text(), "keep?")
        for backup in backups:
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertIn(backup.read_text(), states)
        self.assertEqual(list(self.folder.glob(".settings.json.*.tmp")), [])

    def test_symlinked_settings_stay_linked(self) -> None:
        real = self.folder / "dotfiles" / "settings.json"
        real.parent.mkdir()
        self.settings.rename(real)
        self.settings.symlink_to(real)
        self.assert_preserved(self.install())
        self.assertTrue(self.settings.is_symlink())
        self.assertEqual(real.stat().st_mode & 0o777, 0o600)

    def test_checkout_path_with_line_break_is_refused(self) -> None:
        pack = self.folder / "pack\nline"
        (pack / "scripts").mkdir(parents=True)
        (pack / "hooks").mkdir()
        shutil.copy2(ROOT / "scripts/install-hook.sh", pack / "scripts/install-hook.sh")
        (pack / "hooks/oni-router.sh").write_text("exit 0\n")
        before = self.settings.read_text()
        result = subprocess.run(["bash", str(pack / "scripts/install-hook.sh")], env=self.env,
                                cwd=self.folder, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn("line break", result.stderr)
        self.assertEqual(self.settings.read_text(), before)

if __name__ == "__main__":
    unittest.main()
