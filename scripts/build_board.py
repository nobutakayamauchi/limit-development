#!/usr/bin/env python3
import argparse, datetime as dt, json, os, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://api.github.com"
JST = dt.timezone(dt.timedelta(hours=9))

# PUBLICATION RULE: allowlist only. New internal fields never become public by accident.
PUBLIC_PROJECT_FIELDS = ("name", "repo", "stage", "speed", "now")
PUBLIC_METRIC_FIELDS = ("requests", "shipped", "approval_waiting")
PUBLIC_TOP_FIELDS = ("mode", "main_project", "focus")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def api_json(path):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", "application/vnd.github+json")
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def safe_call(path):
    try:
        return api_json(path)
    except Exception:
        return None


def public_subset(source, fields):
    if not isinstance(source, dict):
        return {field: "UNKNOWN" for field in fields}
    return {field: source.get(field, "UNKNOWN") for field in fields}


def repo_telemetry(repo):
    q = urllib.parse.quote(repo, safe="/")
    commits = safe_call(f"/repos/{q}/commits?per_page=1")
    pulls = safe_call(f"/repos/{q}/pulls?state=open&per_page=10")
    runs = safe_call(f"/repos/{q}/actions/runs?per_page=1")
    latest = commits[0] if isinstance(commits, list) and commits else {}
    workflow_runs = runs.get("workflow_runs") if isinstance(runs, dict) else None
    run = workflow_runs[0] if workflow_runs else {}

    # Do not republish arbitrary commit messages on the public homepage.
    # Public telemetry exposes only low-risk operational facts.
    return {
        "latest_commit_at": ((latest.get("commit") or {}).get("committer") or {}).get("date", "UNKNOWN"),
        "open_prs": len(pulls) if isinstance(pulls, list) else "UNKNOWN",
        "latest_action": run.get("conclusion") or run.get("status") or "UNKNOWN",
    }


def build_current(control):
    now = dt.datetime.now(JST)
    projects = []
    feed = []

    for raw_project in control.get("projects", []):
        p = public_subset(raw_project, PUBLIC_PROJECT_FIELDS)
        repo = p.get("repo")
        tel = repo_telemetry(repo) if isinstance(repo, str) and repo != "UNKNOWN" else {
            "latest_commit_at": "UNKNOWN",
            "open_prs": "UNKNOWN",
            "latest_action": "UNKNOWN",
        }
        item = dict(p)
        item["telemetry"] = tel
        projects.append(item)
        feed.append(
            f"{p.get('name', 'UNKNOWN')}: GitHub activity observed / Actions {tel['latest_action']}"
        )

    metrics = public_subset(control.get("metrics", {}), PUBLIC_METRIC_FIELDS)
    metrics["active_projects"] = sum(1 for p in projects if p.get("speed") not in {"PAUSED"})

    top = public_subset(control, PUBLIC_TOP_FIELDS)
    return {
        **top,
        "last_updated": now.strftime("%Y-%m-%d %H:%M JST"),
        "metrics": metrics,
        "projects": projects,
        "feed": feed[:6],
        "source_note": (
            "Allowlist-only public reconstruction. Arbitrary internal fields and raw commit messages "
            "are not published. UNKNOWN is preserved."
        ),
    }


def build_daily(control, day):
    start_jst = dt.datetime.combine(day, dt.time.min, JST)
    end_jst = start_jst + dt.timedelta(days=1)
    since = start_jst.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    until = end_jst.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    activity = []
    known_total = 0
    incomplete = False

    for raw_project in control.get("projects", []):
        p = public_subset(raw_project, PUBLIC_PROJECT_FIELDS)
        repo = p.get("repo")
        if not isinstance(repo, str) or repo == "UNKNOWN":
            n = "UNKNOWN"
            incomplete = True
        else:
            q = urllib.parse.quote(repo, safe="/")
            commits = safe_call(
                f"/repos/{q}/commits?since={urllib.parse.quote(since)}&until={urllib.parse.quote(until)}&per_page=100"
            )
            if isinstance(commits, list):
                n = len(commits)
                known_total += n
            else:
                n = "UNKNOWN"
                incomplete = True
        activity.append({"name": p.get("name", "UNKNOWN"), "repo": repo, "commits": n})

    public_commit_count = f"PARTIAL:{known_total}" if incomplete else known_total
    top = public_subset(control, PUBLIC_TOP_FIELDS)
    metrics = public_subset(control.get("metrics", {}), PUBLIC_METRIC_FIELDS)

    return {
        "date": day.isoformat(),
        "mode_at_close": top["mode"],
        "main_project_at_close": top["main_project"],
        "focus_at_close": top["focus"],
        "repo_activity": activity,
        "public_commit_count": public_commit_count,
        "requests": metrics["requests"],
        "shipped": metrics["shipped"],
        "approval_waiting": metrics["approval_waiting"],
        "mode_transitions": "UNKNOWN",
        "incidents": "UNKNOWN",
        "major_findings": [],
        "next_focus": "Re-evaluate from the next hourly control cycle",
        "source_note": (
            "One daily public-safe summary. Only allowlisted fields are durable. "
            "Missing non-GitHub business data remains UNKNOWN."
        ),
    }


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rebuild_history_index(history_dir):
    history_dir = pathlib.Path(history_dir)
    files = sorted([p.name for p in history_dir.glob("20??-??-??.json")], reverse=True)
    write_json(history_dir / "index.json", {"days": files})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--daily")
    ap.add_argument("--day")
    args = ap.parse_args()
    control = load_json(ROOT / "data" / "control-state.json")
    if args.output:
        write_json(args.output, build_current(control))
    if args.daily:
        day = dt.date.fromisoformat(args.day) if args.day else dt.datetime.now(JST).date()
        write_json(args.daily, build_daily(control, day))
        rebuild_history_index(pathlib.Path(args.daily).parent)
    if not args.output and not args.daily:
        ap.error("--output or --daily is required")


if __name__ == "__main__":
    main()
