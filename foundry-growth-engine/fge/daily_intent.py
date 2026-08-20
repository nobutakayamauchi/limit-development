from __future__ import annotations

import json
from pathlib import Path
import re

ALLOWED_KEYS = {
    "observation_id", "date", "project", "intent", "source_type",
    "approval_status", "public_safe", "allow_journal", "source_ref"
}
ALLOWED_SOURCE_TYPES = {"goal", "chat_observation"}


def _clean(text):
    return " ".join(str(text or "").split()).strip()


def _norm_project(text):
    return re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]+", " ", _clean(text)).casefold()


def load_daily_intents(path: str | Path):
    """Load only explicitly approved, public-safe daily intent observations.

    Raw chat is intentionally not accepted here. A record must already be a
    distilled observation approved for public JOURNAL use and retain a source
    reference so the published intent can be traced back to its approval gate.
    """
    p = Path(path)
    if not p.exists():
        return []
    out = []
    seen = set()
    with p.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"daily intent at line {lineno} must be an object")
            unknown = set(item) - ALLOWED_KEYS
            if unknown:
                raise ValueError(f"daily intent at line {lineno} has unsupported fields: {sorted(unknown)}")
            required = ("observation_id", "date", "project", "intent", "source_type", "source_ref")
            if any(not _clean(item.get(k)) for k in required):
                raise ValueError(f"daily intent at line {lineno} is missing required fields")
            if item["source_type"] not in ALLOWED_SOURCE_TYPES:
                raise ValueError(f"daily intent at line {lineno} has invalid source_type")
            if item.get("approval_status") != "approved":
                continue
            if item.get("public_safe") is not True or item.get("allow_journal") is not True:
                continue
            oid = _clean(item["observation_id"])
            if oid in seen:
                continue
            seen.add(oid)
            normalized = dict(item)
            normalized["observation_id"] = oid
            normalized["date"] = _clean(item["date"])
            normalized["project"] = _clean(item["project"])
            normalized["intent"] = _clean(item["intent"])
            normalized["source_ref"] = _clean(item["source_ref"])
            out.append(normalized)
    return out


def resolve_daily_intent(intents, date, project, knowledge=None):
    """Resolve a same-day approved intent for the project.

    Exact project names win. Then the same replaceable project aliases used by
    Knowledge may bridge repository-shaped names (e.g. WebAI-Bridge) to the
    public project name. No cross-date fallback exists: old intent must never be
    recycled into a new day's JOURNAL.
    """
    date = _clean(date)
    project = _clean(project)
    same_day = [x for x in intents if x.get("date") == date]
    exact = [x for x in same_day if _norm_project(x.get("project")) == _norm_project(project)]
    if exact:
        return exact[-1]

    aliases = (knowledge or {}).get("project_aliases", []) if isinstance(knowledge, dict) else []
    candidates = {project}
    for alias in aliases:
        if not isinstance(alias, dict):
            continue
        pattern = _clean(alias.get("pattern"))
        target = _clean(alias.get("project"))
        if not pattern or not target:
            continue
        try:
            if re.search(pattern, project, flags=re.I) or re.search(pattern, re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]+", " ", project), flags=re.I):
                candidates.add(target)
        except re.error:
            continue
    candidate_norms = {_norm_project(x) for x in candidates}
    matched = [x for x in same_day if _norm_project(x.get("project")) in candidate_norms]
    return matched[-1] if matched else None
