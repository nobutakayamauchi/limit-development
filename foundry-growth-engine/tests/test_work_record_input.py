from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fge.adapters.github_input import GitHubGitAdapter
from fge.adapters.work_record_input import WorkRecordError, WorkRecordFileAdapter
from fge.core import INTENT_FORCE_ARTICLE, INTENT_RECORD_ONLY


class WorkRecordInputTest(unittest.TestCase):
    def record(self, **overrides):
        data = {
            "schema": "fge.work-record/v0",
            "record_id": "wr_001",
            "session_id": "day_2026-08-19_a",
            "session_sequence": 1,
            "content_scope": "DELTA",
            "record_type": "CHECKPOINT",
            "captured_at": "2026-08-19T12:30:00+09:00",
            "source_type": "AI_SESSION",
            "source_adapter": "test-agent",
            "project": "FOUNDRY GROWTH ENGINE",
            "summary": "Work Record input adapterを追加",
            "evidence_refs": [],
            "media_refs": [],
            "explicit_intent": "AUTO",
            "session_state": "OPEN",
        }
        data.update(overrides)
        return data

    def write(self, root, name="one.json", **overrides):
        path = Path(root, ".fge/records/2026/08/19", name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.record(**overrides), ensure_ascii=False), encoding="utf-8")
        return path

    def test_valid_checkpoint_becomes_existing_evidence_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, changes=[{"what": "JSONを検証", "result": "PASS"}])
            items = WorkRecordFileAdapter(td).collect()
            self.assertEqual(len(items), 1)
            ev = items[0]
            self.assertEqual(ev.source_id, "wr_001")
            self.assertEqual(ev.project_hint, "FOUNDRY GROWTH ENGINE")
            self.assertIn("JSONを検証", ev.text)
            self.assertEqual(ev.raw_evidence_ref, "work-record:.fge/records/2026/08/19/one.json")

    def test_article_checkpoint_forces_article_when_unspecified(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, record_type="ARTICLE_CHECKPOINT")
            ev = WorkRecordFileAdapter(td).collect()[0]
            self.assertEqual(ev.explicit_intent, INTENT_FORCE_ARTICLE)

    def test_record_only_intent_survives_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, explicit_intent="RECORD_ONLY")
            ev = WorkRecordFileAdapter(td).collect()[0]
            self.assertEqual(ev.explicit_intent, INTENT_RECORD_ONLY)

    def test_media_reference_extracts_durable_locator(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, media_refs=[{"kind": "photo", "uri": "s3://private/before.jpg"}])
            ev = WorkRecordFileAdapter(td).collect()[0]
            self.assertEqual(ev.media, ("s3://private/before.jpg",))

    def test_naive_timestamp_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, captured_at="2026-08-19T12:30:00")
            with self.assertRaises(WorkRecordError):
                WorkRecordFileAdapter(td).collect()

    def test_end_day_must_be_sealed(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, record_type="END_DAY", session_state="OPEN")
            with self.assertRaises(WorkRecordError):
                WorkRecordFileAdapter(td).collect()

    def test_only_end_day_may_seal(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, record_type="CHECKPOINT", session_state="SEALED")
            with self.assertRaises(WorkRecordError):
                WorkRecordFileAdapter(td).collect()

    def test_duplicate_session_sequence_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            self.write(td, "one.json", record_id="wr_001", session_sequence=1)
            self.write(td, "two.json", record_id="wr_002", session_sequence=1)
            with self.assertRaises(WorkRecordError):
                WorkRecordFileAdapter(td).collect()

    def test_pure_work_record_transport_commit_is_not_second_git_event(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.check_call(["git", "init", "-q", str(repo)])
            subprocess.check_call(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
            subprocess.check_call(["git", "-C", str(repo), "config", "user.name", "Test"])
            self.write(td)
            subprocess.check_call(["git", "-C", str(repo), "add", ".fge/records"])
            subprocess.check_call(["git", "-C", str(repo), "commit", "-q", "-m", "Save work record"])
            self.assertEqual(GitHubGitAdapter(repo).collect(), [])

    def test_code_commit_still_remains_git_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.check_call(["git", "init", "-q", str(repo)])
            subprocess.check_call(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
            subprocess.check_call(["git", "-C", str(repo), "config", "user.name", "Test"])
            Path(repo, "feature.txt").write_text("work", encoding="utf-8")
            subprocess.check_call(["git", "-C", str(repo), "add", "feature.txt"])
            subprocess.check_call(["git", "-C", str(repo), "commit", "-q", "-m", "Add feature"])
            items = GitHubGitAdapter(repo).collect()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].text, "Add feature")


if __name__ == "__main__":
    unittest.main()
