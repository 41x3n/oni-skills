"""Run the documented merge procedure only in isolated Git repositories."""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntegrationExamplesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.repo = self.folder / "repo"
        self.repo.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_COUNT="1",
                        GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0=os.devnull,
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.test",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.test")
        self.git("init", "-b", "main")
        (self.repo / "local.txt").write_text("original\n")
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.before = self.git("rev-parse", "HEAD")
        remote = self.folder / "remote.git"
        self.git("init", "--bare", str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-u", "origin", "main")
        self.git("checkout", "-b", "feature")
        for number in (1, 2):
            (self.repo / f"feature{number}.txt").write_text(f"feature {number}\n")
            self.git("add", ".")
            self.git("commit", "-m", f"feature {number}")
        self.feature = self.git("rev-parse", "HEAD")
        self.git("checkout", "main")

    def git(self, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=self.repo, env=self.env,
                                capture_output=True, text=True, check=True, timeout=15)
        return result.stdout.strip()

    def merge_example(self, test_command: str) -> subprocess.CompletedProcess[str]:
        document = (ROOT / "skills/ship/references/integrating.md").read_text()
        section = document.split("## Option 1 — merge locally\n", 1)[1]
        match = re.search(r"```bash\n(.*?)\n```", section, re.DOTALL)
        self.assertIsNotNone(match)
        script = match.group(1).replace("<base>", "main").replace("<feature>", "feature")
        script = script.replace("<the project's test command>", test_command)
        # Record the captured commit and detect whether failure allows cleanup.
        script = "trap 'printf %s \"${PRE_MERGE_HEAD:-}\" > captured-head' EXIT\n" + script
        script += "\ntouch cleanup-ran\n"
        return subprocess.run(["bash", "-c", script], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, timeout=15, check=False)

    def test_failed_two_commit_fast_forward_preserves_work_and_stops(self) -> None:
        result = self.merge_example("printf 'later work\\n' > local.txt; false")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.repo / "captured-head").read_text(), self.before)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.feature)
        self.assertEqual((self.repo / "local.txt").read_text(), "later work\n")
        self.assertFalse((self.repo / "cleanup-ran").exists())
        self.assertIn("feature", self.git("branch", "--list", "feature"))

    def test_dirty_checkout_stops_before_merge(self) -> None:
        (self.repo / "local.txt").write_text("existing work\n")
        result = self.merge_example("true")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.before)
        self.assertEqual((self.repo / "local.txt").read_text(), "existing work\n")
        self.assertFalse((self.repo / "cleanup-ran").exists())

    def test_successful_merge_records_exact_previous_commit(self) -> None:
        result = self.merge_example("true")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.repo / "captured-head").read_text(), self.before)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.feature)
        self.assertTrue((self.repo / "cleanup-ran").exists())


if __name__ == "__main__":
    unittest.main()
