import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repo_intake.py"
spec = importlib.util.spec_from_file_location("repo_intake", SCRIPT)
repo_intake = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(repo_intake)


class RepoIntakeTests(unittest.TestCase):
    def test_selects_only_new_nonignored_repos(self):
        config = {
            "created_after": "2026-08-19T07:29:00Z",
            "ignore": ["me/ignore"],
            "skip_forks": True,
            "skip_archived": True,
        }
        repos = [
            {"full_name": "me/old", "created_at": "2026-08-19T07:00:00Z", "fork": False, "archived": False},
            {"full_name": "me/new", "created_at": "2026-08-19T08:00:00Z", "fork": False, "archived": False},
            {"full_name": "me/ignore", "created_at": "2026-08-19T09:00:00Z", "fork": False, "archived": False},
            {"full_name": "me/fork", "created_at": "2026-08-19T09:00:00Z", "fork": True, "archived": False},
        ]
        selected = repo_intake.select_new_repositories(repos, config)
        self.assertEqual([r["full_name"] for r in selected], ["me/new"])

    def test_issue_body_requires_human_wall_ball(self):
        body = repo_intake.build_issue_body({
            "full_name": "me/new-tool",
            "html_url": "https://github.com/me/new-tool",
            "description": "test",
        })
        self.assertIn("回答が終わるまで公開カード / LPは自動生成しません", body)
        self.assertIn("非エンジニア", body)
        self.assertIn("CAROUSEL", body)
        self.assertIn("CTA", body)

    def test_issue_title_is_stable_for_dedupe(self):
        self.assertEqual(repo_intake.issue_title("me/tool"), "[FGE intake] me/tool")


if __name__ == "__main__":
    unittest.main()
