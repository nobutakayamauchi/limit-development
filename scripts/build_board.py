#!/usr/bin/env python3
import argparse, datetime as dt, json, os, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://api.github.com"
JST = dt.timezone(dt.timedelta(hours=9))

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

def repo_telemetry(repo):
    q = urllib.parse.quote(repo, safe="/")
    commits = safe_call(f"/repos/{q}/commits?per_page=1")
    pulls = safe_call(f"/repos/{q}/pulls?state=open&per_page=10")
    runs = safe_call(f"/repos/{q}/actions/runs?per_page=1")
    latest = commits[0] if isinstance(commits, list) and commits else {}
    workflow_runs = runs.get("workflow_runs") if isinstance(runs, dict) else None
    run = workflow_runs[0] if workflow_runs else {}
    return {
        "latest_commit": (latest.get("commit") or {}).get("message", "UNKNOWN").splitlines()[0],
        "latest_commit_at": ((latest.get("commit") or {}).get("committer") or {}).get("date", "UNKNOWN"),
        "open_prs": len(pulls) if isinstance(pulls, list) else "UNKNOWN",
        "latest_action": run.get("conclusion") or run.get("status") or "UNKNOWN"
    }

def build_current(control):
    now = dt.datetime.now(JST)
    projects = []
    feed = []
    for p in control.get("projects", []):
        item = dict(p)
        tel = repo_telemetry(p["repo"])
        item["telemetry"] = tel
        projects.append(item)
        feed.append(f"{p['name']}: {tel['latest_commit']} / Actions {tel['latest_action']}")
    metrics = dict(control.get("metrics", {}))
    metrics["active_projects"] = sum(1 for p in projects if p.get("speed") not in {"PAUSED"})
    return {
        "mode": control.get("mode", "UNKNOWN"),
        "main_project": control.get("main_project", "UNKNOWN"),
        "focus": control.get("focus", "UNKNOWN"),
        "last_updated": now.strftime("%Y-%m-%d %H:%M JST"),
        "metrics": metrics,
        "projects": projects,
        "feed": feed[:6],
        "source_note": "Hourly public-safe reconstruction from control-state plus public GitHub repository telemetry. UNKNOWN is preserved."
    }

def build_daily(control, day):
    start_jst = dt.datetime.combine(day, dt.time.min, JST)
    end_jst = start_jst + dt.timedelta(days=1)
    since = start_jst.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    until = end_jst.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    activity = []
    known_total = 0
    incomplete = False
    for p in control.get("projects", []):
        q = urllib.parse.quote(p["repo"], safe="/")
        commits = safe_call(f"/repos/{q}/commits?since={urllib.parse.quote(since)}&until={urllib.parse.quote(until)}&per_page=100")
        if isinstance(commits, list):
            n = len(commits)
            known_total += n
        else:
            n = "UNKNOWN"
            incomplete = True
        activity.append({"name": p["name"], "repo": p["repo"], "commits": n})
    public_commit_count = f"PARTIAL:{known_total}" if incomplete else known_total
    return {
        "date": day.isoformat(),
        "mode_at_close": control.get("mode", "UNKNOWN"),
        "main_project_at_close": control.get("main_project", "UNKNOWN"),
        "focus_at_close": control.get("focus", "UNKNOWN"),
        "repo_activity": activity,
        "public_commit_count": public_commit_count,
        "requests": (control.get("metrics") or {}).get("requests", "UNKNOWN"),
        "shipped": (control.get("metrics") or {}).get("shipped", "UNKNOWN"),
        "approval_waiting": (control.get("metrics") or {}).get("approval_waiting", "UNKNOWN"),
        "mode_transitions": "UNKNOWN",
        "incidents": "UNKNOWN",
        "major_findings": [],
        "next_focus": "Re-evaluate from the next hourly control cycle",
        "source_note": "One daily public-safe summary. Missing non-GitHub business data remains UNKNOWN."
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
