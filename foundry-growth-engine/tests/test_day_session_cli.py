from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fge.adapters.work_record_input import WorkRecordFileAdapter
from fge.core import build_update, INTENT_FORCE_ARTICLE

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
SCRIPT = ROOT / "scripts" / "day_session.py"


class DaySessionCLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init")
        self.git("config", "user.name", "FGE Test")
        self.git("config", "user.email", "fge-test@example.invalid")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, check=True):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=check,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_cli(self, command, *extra, check=True):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                command,
                "--repo",
                str(self.repo),
                "--project",
                "FOUNDRY GROWTH ENGINE",
                "--summary",
                f"{command} fixture",
                "--session",
                "day_test",
                "--source-adapter",
                "test-agent",
                *extra,
            ],
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and proc.returncode != 0:
            self.fail(f"CLI failed: {proc.stderr}\n{proc.stdout}")
        return proc

    def receipt(self, proc):
        return json.loads(proc.stdout)

    def test_three_command_lifecycle_commits_and_seals(self):
        cp = self.receipt(self.run_cli("checkpoint", "--commit"))
        self.assertEqual(cp["status"], "COMMITTED")
        self.assertEqual(cp["session_sequence"], 1)
        self.assertEqual(cp["session_state"], "OPEN")
        self.assertTrue(cp["commit_sha"])

        article = self.receipt(
            self.run_cli(
                "article",
                "--article-instruction",
                "この記事は実運用のDAY SESSIONを主題にする",
                "--commit",
            )
        )
        self.assertEqual(article["session_sequence"], 2)
        self.assertEqual(article["session_state"], "OPEN")

        evidence = WorkRecordFileAdapter(self.repo).collect()
        article_ev = next(x for x in evidence if x.source_id == article["record_id"])
        self.assertEqual(article_ev.explicit_intent, INTENT_FORCE_ARTICLE)
        self.assertTrue(build_update(article_ev, {}).article_candidate)

        end = self.receipt(self.run_cli("end-day", "--commit"))
        self.assertEqual(end["session_sequence"], 3)
        self.assertEqual(end["session_state"], "SEALED")
        self.assertTrue(end["commit_sha"])

        reopened = self.run_cli("checkpoint", "--commit", check=False)
        self.assertEqual(reopened.returncode, 2)
        self.assertIn("already SEALED", reopened.stderr)

    def test_exact_file_commit_does_not_take_unrelated_staged_change(self):
        unrelated = self.repo / "unrelated.txt"
        unrelated.write_text("keep staged\n", encoding="utf-8")
        self.git("add", "unrelated.txt")

        receipt = self.receipt(self.run_cli("checkpoint", "--commit"))
        names = [
            x.strip()
            for x in self.git("show", "--pretty=format:", "--name-only", receipt["commit_sha"]).stdout.splitlines()
            if x.strip()
        ]
        self.assertEqual(names, [receipt["record_path"]])
        still_staged = self.git("diff", "--cached", "--name-only").stdout.splitlines()
        self.assertIn("unrelated.txt", still_staged)

    def test_failed_commit_rolls_back_record_and_never_returns_receipt(self):
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        before = self.git("rev-parse", "HEAD").stdout.strip()

        proc = self.run_cli("checkpoint", "--commit", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn('"status": "COMMITTED"', proc.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before)
        self.assertEqual(list((self.repo / ".fge").rglob("*.json")), [])

    def test_local_only_is_explicitly_not_a_committed_save(self):
        receipt = self.receipt(self.run_cli("checkpoint"))
        self.assertEqual(receipt["status"], "LOCAL_ONLY")
        self.assertIsNone(receipt["commit_sha"])
        self.assertTrue((self.repo / receipt["record_path"]).exists())

    def test_end_day_rejects_incomplete_media(self):
        proc = self.run_cli(
            "end-day",
            "--media-ref",
            "chat-only://photo-1",
            "--media-state",
            "INCOMPLETE",
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot seal", proc.stderr)
        self.assertEqual(list((self.repo / ".fge").rglob("*.json")), [])

    def test_record_only_checkpoint_stays_source_only(self):
        receipt = self.receipt(self.run_cli("checkpoint", "--intent", "RECORD_ONLY"))
        evidence = WorkRecordFileAdapter(self.repo).collect()
        ev = next(x for x in evidence if x.source_id == receipt["record_id"])
        self.assertEqual(ev.explicit_intent, "RECORD_ONLY")
        self.assertFalse(build_update(ev, {}).article_candidate)


if __name__ == "__main__":
    unittest.main()
