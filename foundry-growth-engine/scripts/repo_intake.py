#!/usr/bin/env python3
"""Detect newly created GitHub repositories and open an FGE intake question.

This belongs to FOUNDRY GROWTH ENGINE because a new repo is a public-output
candidate, not an instruction to auto-publish. Detection only creates the
human wall-ball gate. Card/visual/LP creation happens after the operator answers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

UTC = dt.timezone.utc
INTAKE_PREFIX = "[FGE intake] "


def parse_ts(value: str) -> dt.datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def issue_title(full_name: str) -> str:
    return f"{INTAKE_PREFIX}{full_name}"


def build_issue_body(repo: dict[str, Any]) -> str:
    full_name = repo["full_name"]
    url = repo.get("html_url", "")
    description = (repo.get("description") or "").strip()
    return f"""## 新しいレポを確認しました

**{full_name}**

{url}

{description if description else "説明はまだありません。"}

カルーセルやLPを勝手に作る前に、まず壁打ちします。
**回答が終わるまで公開カード / LPは自動生成しません。**

### まず決めること

1. これはサイトに載せる？ **制作物 / 研究物 / 商品 / 保留 / 記録だけ**
2. 正式名称と通称は？
3. 最初の一言は？ **「○○してください」「○○やめてください」「○○？ここです」** のように、疲れた頭でも意味が入る一文にする。
4. 非エンジニア向けに言うと、何をするもの？
5. 誰の、どんな面倒・困りごとを減らす？
6. 何を入れる？
7. 何が返ってくる？
8. 最後に人が決める / やることは？
9. 一枚絵にするなら、何を見せれば10秒で伝わる？
10. 次の行動は？ **自分で使う / 詳細を見る / 導入相談 / 買う**

### 回答後にFGEが作るもの

```text
CAROUSEL  = 3秒で意味が分かる短文
VISUAL    = 10秒で仕組みが分かる一枚絵
LP        = 困りごと → 解決 → 証拠 → 導入までの3分版
CTA       = 次に何をしてほしいか
```

公開は従来どおり人間のレビューゲートを通します。
"""


def select_new_repositories(repos: Iterable[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    threshold = parse_ts(config["created_after"])
    ignored = set(config.get("ignore", []))
    skip_forks = bool(config.get("skip_forks", True))
    skip_archived = bool(config.get("skip_archived", True))
    selected: list[dict[str, Any]] = []

    for repo in repos:
        full_name = repo.get("full_name")
        created_at = repo.get("created_at")
        if not full_name or not created_at:
            continue
        if full_name in ignored:
            continue
        if skip_forks and repo.get("fork"):
            continue
        if skip_archived and repo.get("archived"):
            continue
        if parse_ts(created_at) <= threshold:
            continue
        selected.append(repo)

    return sorted(selected, key=lambda r: parse_ts(r["created_at"]))


def request_json(url: str, *, token: str | None = None, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "foundry-growth-engine-repo-intake",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc


def paged(url: str, token: str | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    page = 1
    sep = "&" if "?" in url else "?"
    while True:
        batch = request_json(f"{url}{sep}per_page=100&page={page}", token=token)
        if not batch:
            break
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def list_source_repositories(owner: str, private_token: str | None) -> list[dict[str, Any]]:
    if private_token:
        repos = paged(
            "https://api.github.com/user/repos?affiliation=owner&visibility=all&sort=created&direction=desc",
            token=private_token,
        )
        return [r for r in repos if (r.get("owner") or {}).get("login", "").lower() == owner.lower()]

    owner_q = urllib.parse.quote(owner, safe="")
    return paged(
        f"https://api.github.com/users/{owner_q}/repos?type=owner&sort=created&direction=desc"
    )


def existing_issue_titles(target_repo: str, issue_token: str) -> set[str]:
    owner, repo = target_repo.split("/", 1)
    url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/issues?state=all"
    issues = paged(url, token=issue_token)
    return {i.get("title", "") for i in issues if "pull_request" not in i}


def create_intake_issue(target_repo: str, repo: dict[str, Any], issue_token: str) -> dict[str, Any]:
    owner, target = target_repo.split("/", 1)
    url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(target)}/issues"
    return request_json(
        url,
        token=issue_token,
        method="POST",
        payload={"title": issue_title(repo["full_name"]), "body": build_issue_body(repo)},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="foundry-growth-engine/config/repo-intake.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    private_token = os.getenv("FGE_REPO_INTAKE_TOKEN") or None
    issue_token = os.getenv("GITHUB_TOKEN") or ""

    repos = list_source_repositories(config["owner"], private_token)
    candidates = select_new_repositories(repos, config)

    if args.dry_run:
        print(json.dumps({"candidates": [r["full_name"] for r in candidates]}, ensure_ascii=False, indent=2))
        return 0

    if not issue_token:
        print("GITHUB_TOKEN is required to create FGE intake issues", file=sys.stderr)
        return 2

    existing = existing_issue_titles(config["target_repo"], issue_token)
    created: list[str] = []
    for repo in candidates:
        title = issue_title(repo["full_name"])
        if title in existing:
            continue
        create_intake_issue(config["target_repo"], repo, issue_token)
        created.append(repo["full_name"])

    print(json.dumps({"detected": len(candidates), "created_intakes": created}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
