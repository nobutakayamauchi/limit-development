from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from ..core import (
    Evidence,
    INTENT_AUTO,
    INTENT_FORCE_ARTICLE,
    INTENT_RECORD_ONLY,
)

SCHEMA = "fge.work-record/v0"
RECORD_TYPES = {"CHECKPOINT", "ARTICLE_CHECKPOINT", "END_DAY", "AUTO_EVENT"}
SOURCE_TYPES = {"AI_SESSION", "GIT_EVENT", "FIELD_CAPTURE", "MANUAL_IMPORT"}
INTENTS = {INTENT_AUTO, INTENT_RECORD_ONLY, INTENT_FORCE_ARTICLE}
SESSION_STATES = {"OPEN", "SEALED"}
CONTENT_SCOPES = {"DELTA", "SNAPSHOT"}


class WorkRecordError(ValueError):
    """Raised when a durable Work Record is ambiguous or invalid."""


class WorkRecordFileAdapter:
    """Read provider-neutral FGE Work Record JSON files from a Git work ledger.

    The adapter deliberately owns no chat/provider behavior. A ChatGPT, Codex,
    Claude, NAGI, field-capture, or manual bridge only needs to persist the
    protocol file. This adapter turns that durable file into the existing FGE
    Evidence boundary.
    """

    def __init__(self, repo_path=".", records_dir=".fge/records", max_records=1000):
        self.repo_path = Path(repo_path)
        self.records_dir = Path(records_dir)
        self.max_records = max_records

    @property
    def root(self) -> Path:
        if self.records_dir.is_absolute():
            return self.records_dir
        return self.repo_path / self.records_dir

    def _required_text(self, data, key, path):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise WorkRecordError(f"{path}: {key} must be a non-empty string")
        return value.strip()

    def _captured_at(self, data, path):
        value = self._required_text(data, "captured_at", path)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WorkRecordError(f"{path}: captured_at must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise WorkRecordError(f"{path}: captured_at must include a timezone")
        return value

    def _media_refs(self, data, path):
        raw = data.get("media_refs", [])
        if not isinstance(raw, list):
            raise WorkRecordError(f"{path}: media_refs must be a list")
        refs = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                refs.append(item.strip())
                continue
            if isinstance(item, dict):
                for key in ("ref", "uri", "path", "object_id"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        refs.append(value.strip())
                        break
        return tuple(refs)

    def _text(self, data, path):
        summary = self._required_text(data, "summary", path)
        parts = [summary]
        changes = data.get("changes", [])
        if changes is not None and not isinstance(changes, list):
            raise WorkRecordError(f"{path}: changes must be a list when present")
        for item in changes or []:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                for key in ("what", "why", "result"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value.strip())
        for key in ("why", "result"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        return "\n".join(dict.fromkeys(parts))

    def _load(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkRecordError(f"{path}: unreadable Work Record: {exc}") from exc
        if not isinstance(data, dict):
            raise WorkRecordError(f"{path}: Work Record must be a JSON object")
        if data.get("schema") != SCHEMA:
            raise WorkRecordError(f"{path}: unsupported schema {data.get('schema')!r}")

        record_id = self._required_text(data, "record_id", path)
        session_id = self._required_text(data, "session_id", path)
        record_type = self._required_text(data, "record_type", path)
        source_type = self._required_text(data, "source_type", path)
        source_adapter = self._required_text(data, "source_adapter", path)
        project = self._required_text(data, "project", path)
        intent = self._required_text(data, "explicit_intent", path)
        session_state = self._required_text(data, "session_state", path)
        content_scope = self._required_text(data, "content_scope", path)

        if record_type not in RECORD_TYPES:
            raise WorkRecordError(f"{path}: unknown record_type {record_type!r}")
        if source_type not in SOURCE_TYPES:
            raise WorkRecordError(f"{path}: unknown source_type {source_type!r}")
        if intent not in INTENTS:
            raise WorkRecordError(f"{path}: unknown explicit_intent {intent!r}")
        if session_state not in SESSION_STATES:
            raise WorkRecordError(f"{path}: unknown session_state {session_state!r}")
        if content_scope not in CONTENT_SCOPES:
            raise WorkRecordError(f"{path}: unknown content_scope {content_scope!r}")

        sequence = data.get("session_sequence")
        if not isinstance(sequence, int) or sequence < 1:
            raise WorkRecordError(f"{path}: session_sequence must be an integer >= 1")
        if record_type == "END_DAY" and session_state != "SEALED":
            raise WorkRecordError(f"{path}: END_DAY must be SEALED after persistence checks")
        if record_type != "END_DAY" and session_state == "SEALED":
            raise WorkRecordError(f"{path}: only END_DAY may seal a DAY SESSION")
        if record_type == "ARTICLE_CHECKPOINT" and intent == INTENT_AUTO:
            intent = INTENT_FORCE_ARTICLE

        evidence_refs = data.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            raise WorkRecordError(f"{path}: evidence_refs must be a list")

        rel = path
        try:
            rel = path.relative_to(self.repo_path)
        except ValueError:
            pass

        return {
            "record_id": record_id,
            "session_id": session_id,
            "sequence": sequence,
            "evidence": Evidence(
                source_id=record_id,
                captured_at=self._captured_at(data, path),
                actor=str(data.get("actor") or source_adapter),
                text=self._text(data, path),
                source_type=f"work_record:{source_type.lower()}",
                project_hint=project,
                explicit_intent=intent,
                raw_evidence_ref=f"work-record:{rel.as_posix()}",
                media=self._media_refs(data, path),
            ),
        }

    def collect(self):
        if not self.root.exists():
            return []
        paths = sorted(self.root.rglob("*.json"))
        loaded = [self._load(path) for path in paths[-self.max_records :]]

        record_ids = set()
        session_sequences = set()
        for item in loaded:
            record_id = item["record_id"]
            if record_id in record_ids:
                raise WorkRecordError(f"duplicate record_id: {record_id}")
            record_ids.add(record_id)
            key = (item["session_id"], item["sequence"])
            if key in session_sequences:
                raise WorkRecordError(
                    f"duplicate session_sequence: session={key[0]} sequence={key[1]}"
                )
            session_sequences.add(key)

        return [
            item["evidence"]
            for item in sorted(
                loaded,
                key=lambda x: (x["evidence"].captured_at, x["record_id"]),
                reverse=True,
            )
        ]
