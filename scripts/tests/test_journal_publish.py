from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_journal_publish import prepare_journal_publish


class JournalPublicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "public"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.bundle = Path(self.tmp.name) / "bundle"
        self.bundle.mkdir()
        (self.bundle / "data").mkdir()
        (self.bundle / "journal").mkdir()
        self.fallback = {p.name: p.read_bytes() for p in (self.root / "journal").glob("2026-08-*.html")}

    def bundle_days(self, days):
        (self.bundle / "data/journals.json").write_text(json.dumps([{"date": day} for day in days]))
        for day in days:
            (self.bundle / "journal" / f"{day}.html").write_text('<html><a href="../../archive/">INDEX</a></html>')

    def snapshot(self):
        return {p.name: p.read_bytes() for p in (self.root / "journal").iterdir()}

    def test_rolling_refresh_preserves_fallback_and_repairs_old_bundle_links(self):
        self.bundle_days(["2026-11-13"])
        prepare_journal_publish(self.bundle, self.root)
        expected = {*self.fallback, "index.html", "2026-11-13.html"}
        self.assertEqual(set(self.snapshot()), expected)
        for name, content in self.fallback.items():
            self.assertEqual((self.root / "journal" / name).read_bytes(), content)
        self.assertEqual((self.root / "journal/index.html").read_bytes(),
                         (self.root / "foundry-growth-engine/templates/journal-index.html").read_bytes())
        self.assertIn('href="../archive/"', (self.root / "journal/2026-11-13.html").read_text())
        subprocess.run([sys.executable, "scripts/check_homepage.py"], cwd=self.root, check=True, capture_output=True)
        before = self.snapshot()
        prepare_journal_publish(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_empty_window_retains_static_destinations(self):
        self.bundle_days([])
        shutil.rmtree(self.bundle / "journal")
        prepare_journal_publish(self.bundle, self.root)
        self.assertEqual(set(self.snapshot()), {*self.fallback, "index.html"})

    def test_generated_date_cannot_overwrite_static_article(self):
        self.bundle_days(["2026-08-19"])
        prepare_journal_publish(self.bundle, self.root)
        self.assertEqual((self.root / "journal/2026-08-19.html").read_bytes(), self.fallback["2026-08-19.html"])

    def test_missing_generated_article_fails_before_replacement(self):
        self.bundle_days(["2026-11-13"])
        (self.bundle / "journal/2026-11-13.html").unlink()
        before = self.snapshot()
        with self.assertRaises(FileNotFoundError):
            prepare_journal_publish(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_missing_fallback_fails_before_replacement(self):
        self.bundle_days([])
        (self.root / "journal/2026-08-19.html").unlink()
        before = self.snapshot()
        with self.assertRaises(FileNotFoundError):
            prepare_journal_publish(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_missing_index_is_still_a_contract_failure(self):
        (self.root / "journal/index.html").unlink()
        result = subprocess.run([sys.executable, "scripts/check_homepage.py"], cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required homepage asset: journal/index.html", result.stderr)

    def test_both_workflow_precommit_steps_preserve_contract(self):
        # Execute the actual publish shell up to git, in an isolated copy.
        # No commit, push, API access or workflow dispatch is performed.
        for name, heading, source in (
            ("fge-hourly.yml", "Publish hourly UPDATE + JOURNAL board", "/tmp/fge-public"),
            ("fge-publish.yml", "Publish reviewed bundle", "/tmp/fge-review/site"),
        ):
            with self.subTest(workflow=name):
                for directory in ("updates", "journal", "archive", "data"):
                    shutil.copytree(ROOT / directory, self.bundle / directory, dirs_exist_ok=True)
                (self.bundle / "articles").mkdir(exist_ok=True)
                workflow = (ROOT / ".github/workflows" / name).read_text()
                step = workflow.split(f"      - name: {heading}\n", 1)[1]
                shell = step.split("        run: |\n", 1)[1].split("          git config", 1)[0]
                shell = "\n".join(line[10:] for line in shell.splitlines())
                shell = shell.replace(source, str(self.bundle))
                subprocess.run(["bash", "-e", "-c", shell], cwd=self.root, check=True, capture_output=True)
                for article, content in self.fallback.items():
                    self.assertEqual((self.root / "journal" / article).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
