import json
import tempfile
import unittest
from pathlib import Path

from scripts import measure


class ScanCodexTests(unittest.TestCase):
    def test_reports_root_session_and_ignores_child_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root_session = [
                {"timestamp": "2026-09-28T18:00:00Z", "type": "session_meta", "payload": {"id": "root", "parent_thread_id": None}},
                {"timestamp": "2026-09-28T18:01:00Z", "type": "turn_context", "payload": {}},
                {"timestamp": "2026-09-28T19:00:00Z", "type": "event_msg", "payload": {"type": "task_started"}},
                {"timestamp": "2026-09-28T20:00:00Z", "type": "compacted", "payload": {}},
                {"timestamp": "2026-09-28T23:00:00Z", "type": "token_usage_record", "payload": {"thread_token_usage": {"total_tokens": 42_000_000}}},
            ]
            child_session = [
                {"timestamp": "2026-09-28T18:30:00Z", "type": "session_meta", "payload": {"id": "child", "parent_thread_id": "root"}},
                {"timestamp": "2026-09-28T18:31:00Z", "type": "token_usage_record", "payload": {"thread_token_usage": {"total_tokens": 9_000}}},
            ]
            for name, records in (("root.jsonl", root_session), ("child.jsonl", child_session)):
                (root / name).write_text("\n".join(json.dumps(record) for record in records))

            sessions = measure.scan_codex(root, cutoff=0)

            self.assertEqual(len(sessions), 1)
            session = sessions[0]
            self.assertEqual(session.session_id, "root")
            self.assertEqual(session.duration_seconds, 5 * 60 * 60)
            self.assertEqual(session.turns, 1)
            self.assertEqual(session.compactions, 1)
            self.assertEqual(session.subagent_tasks, 1)
            self.assertEqual(session.total_tokens, 42_000_000)


if __name__ == "__main__":
    unittest.main()
