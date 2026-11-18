import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse

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


class RepoIntakeAPITests(unittest.TestCase):
    def setUp(self):
        # All credentials are synthetic; an unconfigured request fails locally.
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.urlopen = self.enterContext(patch.object(
            repo_intake.urllib.request, "urlopen",
            side_effect=AssertionError("Unexpected API request"),
        ))
        self.stdout = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        temp = self.enterContext(tempfile.TemporaryDirectory())
        self.config = Path(temp) / "intake.json"
        self.config.write_text(json.dumps({
            "owner": "me", "target_repo": "me/site",
            "created_after": "2026-08-19T07:29:00Z",
        }), encoding="utf-8")
        self.repo = {
            "full_name": "me/new", "owner": {"login": "me"},
            "created_at": "2026-08-19T08:00:00Z", "private": False,
        }

    @staticmethod
    def response(payload):
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    def run_main(self, *, dry_run=True):
        return repo_intake.main([
            "--config", str(self.config), *(["--dry-run"] if dry_run else []),
        ])

    def requests(self):
        return [call.args[0] for call in self.urlopen.call_args_list]

    def test_github_token_authenticates_public_fetch_when_private_token_missing_or_empty(self):
        for private_env in ({}, {"FGE_REPO_INTAKE_TOKEN": ""}):
            with self.subTest(private_env=private_env), patch.dict(
                os.environ, {"GITHUB_TOKEN": "actions-test-token", **private_env}, clear=True,
            ):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = [self.response([self.repo])]
                self.assertEqual(self.run_main(), 0)
                self.assertEqual(self.urlopen.call_count, 1)
                req = self.requests()[0]
                self.assertEqual(urllib.parse.urlsplit(req.full_url).path, "/users/me/repos")
                self.assertEqual(req.get_header("Authorization"), "Bearer actions-test-token")
                self.assertEqual(req.get_method(), "GET")

    def test_public_authentication_is_preserved_across_pages(self):
        os.environ["GITHUB_TOKEN"] = "actions-test-token"
        self.urlopen.side_effect = [
            self.response([self.repo] * 100), self.response([]),
        ]
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.urlopen.call_count, 2)
        for page, req in enumerate(self.requests(), start=1):
            parts = urllib.parse.urlsplit(req.full_url)
            self.assertEqual(parts.path, "/users/me/repos")
            self.assertEqual(urllib.parse.parse_qs(parts.query), {
                "type": ["owner"], "sort": ["created"], "direction": ["desc"],
                "per_page": ["100"], "page": [str(page)],
            })
            self.assertEqual(req.get_header("Authorization"), "Bearer actions-test-token")

    def test_private_token_preserves_private_endpoint_and_owner_filter(self):
        os.environ.update(FGE_REPO_INTAKE_TOKEN="private-test-token", GITHUB_TOKEN="actions-test-token")
        private_repo = {**self.repo, "private": True, "owner": {"login": "ME"}}
        other_repo = {**self.repo, "full_name": "other/hidden", "owner": {"login": "other"}}
        self.urlopen.side_effect = [self.response([private_repo, other_repo])]
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(json.loads(self.stdout.getvalue()), {"candidates": ["me/new"]})
        self.assertEqual(self.urlopen.call_count, 1)
        req = self.requests()[0]
        parts = urllib.parse.urlsplit(req.full_url)
        self.assertEqual(parts.path, "/user/repos")
        self.assertEqual(urllib.parse.parse_qs(parts.query), {
            "affiliation": ["owner"], "visibility": ["all"], "sort": ["created"],
            "direction": ["desc"], "per_page": ["100"], "page": ["1"],
        })
        self.assertEqual(req.get_header("Authorization"), "Bearer private-test-token")

    def test_no_tokens_preserves_anonymous_public_dry_run(self):
        self.urlopen.side_effect = [self.response([self.repo])]
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(json.loads(self.stdout.getvalue()), {"candidates": ["me/new"]})
        self.assertEqual(self.urlopen.call_count, 1)
        req = self.requests()[0]
        self.assertEqual(urllib.parse.urlsplit(req.full_url).path, "/users/me/repos")
        self.assertIsNone(req.get_header("Authorization"))

    def test_missing_issue_token_never_creates_an_issue(self):
        for tokens in ({}, {"FGE_REPO_INTAKE_TOKEN": "private-test-token"}):
            with self.subTest(tokens=tokens), patch.dict(os.environ, tokens, clear=True):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = [self.response([self.repo])]
                self.assertEqual(self.run_main(dry_run=False), 2)
                self.assertEqual(self.urlopen.call_count, 1)
                self.assertEqual(self.requests()[0].get_method(), "GET")
        self.assertIn("GITHUB_TOKEN is required", self.stderr.getvalue())

    def test_issue_operations_keep_github_token_and_existing_review_gate(self):
        os.environ.update(FGE_REPO_INTAKE_TOKEN="private-test-token", GITHUB_TOKEN="actions-test-token")
        self.urlopen.side_effect = [
            self.response([self.repo]), self.response([]), self.response({"number": 1}),
        ]
        self.assertEqual(self.run_main(dry_run=False), 0)
        requests = self.requests()
        self.assertEqual([req.get_method() for req in requests], ["GET", "GET", "POST"])
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer private-test-token")
        for req in requests[1:]:
            self.assertEqual(req.get_header("Authorization"), "Bearer actions-test-token")
            self.assertEqual(urllib.parse.urlsplit(req.full_url).path, "/repos/me/site/issues")
        body = json.loads(requests[2].data)
        self.assertEqual(body["title"], "[FGE intake] me/new")
        self.assertIn("回答が終わるまで公開カード / LPは自動生成しません", body["body"])
        self.assertIn("公開は従来どおり人間のレビューゲートを通します", body["body"])

    def test_existing_intake_is_not_created_again(self):
        os.environ["GITHUB_TOKEN"] = "actions-test-token"
        self.urlopen.side_effect = [
            self.response([self.repo]), self.response([{"title": "[FGE intake] me/new"}]),
        ]
        self.assertEqual(self.run_main(dry_run=False), 0)
        self.assertEqual([req.get_method() for req in self.requests()], ["GET", "GET"])
        self.assertEqual(json.loads(self.stdout.getvalue())["created_intakes"], [])

    def test_http_failures_stop_before_issue_access_without_anonymous_retry(self):
        cases = [
            (401, "Bad credentials"), (403, "API rate limit exceeded"),
            (403, "Resource not accessible by integration"),
            (429, "You have exceeded a secondary rate limit"), (500, "Internal Server Error"),
        ]
        for private_token in (None, "private-test-token"):
            for code, message in cases:
                with self.subTest(private_token=private_token, code=code, message=message):
                    os.environ.clear()
                    os.environ["GITHUB_TOKEN"] = "actions-test-token"
                    if private_token:
                        os.environ["FGE_REPO_INTAKE_TOKEN"] = private_token
                    self.urlopen.reset_mock()
                    self.urlopen.side_effect = urllib.error.HTTPError(
                        "https://api.github.com/test", code, message, {},
                        self.response({"message": message}),
                    )
                    with self.assertRaisesRegex(RuntimeError, f"GitHub API {code}:.*{message}"):
                        self.run_main(dry_run=False)
                    self.assertEqual(self.urlopen.call_count, 1)
                    req = self.requests()[0]
                    self.assertEqual(req.get_method(), "GET")
                    self.assertEqual(req.get_header("Authorization"), f"Bearer {private_token or 'actions-test-token'}")

    def test_later_page_rate_limit_does_not_process_partial_repositories(self):
        os.environ["GITHUB_TOKEN"] = "actions-test-token"
        self.urlopen.side_effect = [
            self.response([self.repo] * 100),
            urllib.error.HTTPError(
                "https://api.github.com/test", 403, "Forbidden", {},
                self.response({"message": "API rate limit exceeded"}),
            ),
        ]
        with self.assertRaisesRegex(RuntimeError, "GitHub API 403:.*API rate limit exceeded"):
            self.run_main(dry_run=False)
        self.assertEqual(self.urlopen.call_count, 2)
        for req in self.requests():
            self.assertEqual(urllib.parse.urlsplit(req.full_url).path, "/users/me/repos")
            self.assertEqual(req.get_method(), "GET")
        self.assertEqual(self.stdout.getvalue(), "")

    def test_network_or_invalid_json_failure_does_not_access_issues(self):
        os.environ["GITHUB_TOKEN"] = "actions-test-token"
        for failure, exception in (
            (urllib.error.URLError("connection unavailable"), urllib.error.URLError),
            (io.BytesIO(b"not JSON"), json.JSONDecodeError),
        ):
            with self.subTest(exception=exception):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = [failure]
                with self.assertRaises(exception):
                    self.run_main(dry_run=False)
                self.assertEqual(self.urlopen.call_count, 1)
                self.assertEqual(self.requests()[0].get_method(), "GET")


if __name__ == "__main__":
    unittest.main()
