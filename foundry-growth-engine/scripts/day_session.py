from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from fge.adapters.work_record_input import (  # noqa: E402
    INTENT_AUTO,
    INTENT_FORCE_ARTICLE,
    INTENT_RECORD_ONLY,
    SCHEMA,
    WorkRecordFileAdapter,
)

MEDIA_STATES = {"NONE", "REFERENCED", "PERSISTED", "INCOMPLETE"}


class DaySessionError(RuntimeError):
    pass


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git command failed"
        raise DaySessionError(detail)
    return proc


def _git_root(repo: str | Path) -> Path:
    candidate = Path(repo).resolve()
    proc = _git(candidate, "rev-parse", "--show-toplevel")
    return Path(proc.stdout.strip()).resolve()


def _slug(value: str) -> str:
    out = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー._-]+", "-", value.strip()).strip("-._")
    return (out or "work")[:64]


def _now(timezone_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone_name))
    except Exception as exc:  # ZoneInfo raises several platform-specific errors.
        raise DaySessionError(f"invalid timezone: {timezone_name}") from exc


def _load_session_records(root: Path, records_dir: str, session_id: str) -> list[dict]:
    base = root / records_dir
    if not base.exists():
        return []
    records = []
    for path in sorted(base.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("schema") == SCHEMA and data.get("session_id") == session_id:
            data = dict(data)
            data["_path"] = path
            records.append(data)
    return records


def _next_sequence(records: list[dict]) -> int:
    seqs = [x.get("session_sequence") for x in records if isinstance(x.get("session_sequence"), int)]
    if len(seqs) != len(set(seqs)):
        raise DaySessionError("duplicate session_sequence already exists; repair ledger before continuing")
    return (max(seqs) if seqs else 0) + 1


def _ensure_open(records: list[dict], session_id: str) -> None:
    if any(x.get("record_type") == "END_DAY" or x.get("session_state") == "SEALED" for x in records):
        raise DaySessionError(f"session is already SEALED: {session_id}")


def _record_path(root: Path, records_dir: str, captured: datetime, record_id: str) -> Path:
    return (
        root
        / records_dir
        / captured.strftime("%Y")
        / captured.strftime("%m")
        / captured.strftime("%d")
        / f"{captured.strftime('%Y%m%dT%H%M%S%z')}-{record_id}.json"
    )


def _write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _rollback_new_record(root: Path, path: Path) -> None:
    try:
        rel = path.relative_to(root).as_posix()
        _git(root, "reset", "--quiet", "--", rel, check=False)
    finally:
        path.unlink(missing_ok=True)


def _commit_exact_file(root: Path, path: Path, message: str) -> str:
    rel = path.relative_to(root).as_posix()
    _git(root, "add", "--", rel)
    proc = _git(root, "commit", "-m", message, "--only", "--", rel, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git commit failed"
        raise DaySessionError(detail)
    sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    names = [x.strip() for x in _git(root, "show", "--pretty=format:", "--name-only", sha).stdout.splitlines() if x.strip()]
    if names != [rel]:
        raise DaySessionError(f"commit boundary violation: expected only {rel}, got {names}")
    return sha


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persist one FGE DAY SESSION checkpoint as fge.work-record/v0."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", default=".")
        p.add_argument("--records-dir", default=".fge/records")
        p.add_argument("--project", required=True)
        p.add_argument("--summary", required=True)
        p.add_argument("--session")
        p.add_argument("--timezone", default="Asia/Tokyo")
        p.add_argument("--source-adapter", default="agent")
        p.add_argument(
            "--source-type",
            default="AI_SESSION",
            choices=["AI_SESSION", "FIELD_CAPTURE", "MANUAL_IMPORT"],
        )
        p.add_argument("--actor")
        p.add_argument("--evidence-ref", action="append", default=[])
        p.add_argument("--media-ref", action="append", default=[])
        p.add_argument("--media-state", choices=sorted(MEDIA_STATES))
        p.add_argument("--privacy-class", default="INTERNAL")
        p.add_argument("--change", action="append", default=[])
        p.add_argument("--why")
        p.add_argument("--result")
        p.add_argument("--next-action")
        p.add_argument("--open-loop", action="append", default=[])
        p.add_argument("--commit", action="store_true", help="commit only the new Work Record and return a commit SHA")

    checkpoint = sub.add_parser("checkpoint", help="ここまで保存 / keep session open")
    add_common(checkpoint)
    checkpoint.add_argument(
        "--intent",
        default=INTENT_AUTO,
        choices=[INTENT_AUTO, INTENT_RECORD_ONLY],
    )

    article = sub.add_parser("article", help="これ一本 / force article candidate and keep session open")
    add_common(article)
    article.add_argument("--article-instruction")

    end_day = sub.add_parser("end-day", help="今日は終わり / persist final delta and seal source session")
    add_common(end_day)
    end_day.add_argument(
        "--intent",
        default=INTENT_AUTO,
        choices=[INTENT_AUTO, INTENT_RECORD_ONLY],
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = _git_root(args.repo)
    captured = _now(args.timezone)
    session_id = args.session or f"day_{captured.strftime('%Y-%m-%d')}_{_slug(args.project)}"
    existing = _load_session_records(root, args.records_dir, session_id)
    _ensure_open(existing, session_id)
    sequence = _next_sequence(existing)

    if args.command == "article":
        record_type = "ARTICLE_CHECKPOINT"
        intent = INTENT_FORCE_ARTICLE
        session_state = "OPEN"
    elif args.command == "end-day":
        record_type = "END_DAY"
        intent = args.intent
        session_state = "SEALED"
    else:
        record_type = "CHECKPOINT"
        intent = args.intent
        session_state = "OPEN"

    media_state = args.media_state or ("REFERENCED" if args.media_ref else "NONE")
    if media_state == "NONE" and args.media_ref:
        raise DaySessionError("media_state NONE conflicts with supplied media refs")
    if media_state in {"REFERENCED", "PERSISTED"} and not args.media_ref:
        raise DaySessionError(f"media_state {media_state} requires at least one --media-ref")
    if args.command == "end-day" and media_state == "INCOMPLETE":
        raise DaySessionError("END_DAY cannot seal while required media is INCOMPLETE")

    token = uuid.uuid4().hex[:10]
    record_id = f"wr_{captured.strftime('%Y%m%d_%H%M%S')}_{sequence:03d}_{token}"
    path = _record_path(root, args.records_dir, captured, record_id)

    record = {
        "schema": SCHEMA,
        "record_id": record_id,
        "session_id": session_id,
        "session_sequence": sequence,
        "content_scope": "DELTA",
        "record_type": record_type,
        "captured_at": captured.isoformat(timespec="seconds"),
        "source_type": args.source_type,
        "source_adapter": args.source_adapter,
        "project": args.project,
        "summary": args.summary,
        "evidence_refs": list(dict.fromkeys(args.evidence_ref)),
        "explicit_intent": intent,
        "session_state": session_state,
        "privacy_class": args.privacy_class,
    }
    if args.actor:
        record["actor"] = args.actor
    if args.media_ref:
        record["media_refs"] = list(dict.fromkeys(args.media_ref))
    if args.change:
        record["changes"] = list(dict.fromkeys(args.change))
    if args.why:
        record["why"] = args.why
    if args.result:
        record["result"] = args.result
    if args.next_action:
        record["next_action"] = args.next_action
    if args.open_loop:
        record["open_loops"] = list(dict.fromkeys(args.open_loop))
    if args.command == "article" and args.article_instruction:
        record["article_instruction"] = args.article_instruction
    if existing:
        record["parent_record_id"] = sorted(
            existing,
            key=lambda x: int(x.get("session_sequence", 0)),
        )[-1].get("record_id")

    _write_atomic(path, record)
    try:
        # Validate the complete ledger using the exact existing FGE intake boundary.
        WorkRecordFileAdapter(root, args.records_dir).collect()
    except Exception:
        path.unlink(missing_ok=True)
        raise

    commit_sha = None
    durability = "LOCAL_ONLY"
    if args.commit:
        try:
            commit_sha = _commit_exact_file(
                root,
                path,
                f"[FGE] {record_type} {session_id} #{sequence}",
            )
            durability = "COMMITTED"
        except Exception:
            _rollback_new_record(root, path)
            raise

    receipt = {
        "status": durability,
        "record_id": record_id,
        "record_path": path.relative_to(root).as_posix(),
        "session_id": session_id,
        "session_sequence": sequence,
        "session_state": session_state,
        "commit_sha": commit_sha,
        "media_state": media_state,
        "saved_at": captured.isoformat(timespec="seconds"),
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DaySessionError as exc:
        print(f"FGE_DAY_SESSION_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
