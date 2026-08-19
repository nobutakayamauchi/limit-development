from __future__ import annotations

from copy import deepcopy
import json
import re
from pathlib import Path


def load_jsonl(path: str | Path):
    items = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"chat item at line {lineno} must be an object")
            if not item.get("source_id") or not item.get("text"):
                raise ValueError(f"chat item at line {lineno} needs source_id and text")
            items.append(item)
    return items


def load_rules(path: str | Path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rules = data.get("rules", []) if isinstance(data, dict) else []
    if not isinstance(rules, list):
        raise ValueError("distiller rules must be a list")
    return data


def _confidence(rule, count: int) -> float:
    base = float(rule.get("base_confidence", 0.6))
    step = float(rule.get("confidence_step", 0.08))
    cap = float(rule.get("max_confidence", 0.95))
    minimum = int(rule.get("min_observations", 2))
    return round(min(cap, base + max(0, count - minimum + 1) * step), 3)


def distill(entries, base_knowledge, rules_config):
    """Build a derived public Knowledge pack from allowlisted chat observations.

    Raw chat text is never copied into the derived pack. It only contributes to
    deterministic observation counts. Observed projects are provenance only;
    a rule becomes project-scoped only when the rule config explicitly says so.
    """
    unique = {}
    for item in entries:
        sid = str(item.get("source_id", "")).strip()
        if not sid or sid in unique:
            continue
        if item.get("allow_public_learning") is not True:
            continue
        unique[sid] = item

    promoted = []
    candidates = []
    for rule in rules_config.get("rules", []):
        rid = str(rule.get("id", "")).strip()
        pattern = str(rule.get("chat_pattern", "")).strip()
        context = str(rule.get("public_context", "")).strip()
        applies_to = str(rule.get("applies_to", "")).strip()
        scope_projects = [str(x) for x in rule.get("scope_projects", []) if str(x).strip()]
        if not rid or not pattern or not context or not applies_to:
            raise ValueError("each distiller rule needs id, chat_pattern, applies_to and public_context")

        matches = []
        observed_projects = set()
        for sid, item in unique.items():
            text = str(item.get("text", ""))
            if re.search(pattern, text, flags=re.I):
                matches.append(sid)
                project = str(item.get("project", "")).strip()
                if project:
                    observed_projects.add(project)

        minimum = int(rule.get("min_observations", 2))
        confidence = _confidence(rule, len(matches)) if matches else 0.0
        record = {
            "id": rid,
            "observation_count": len(matches),
            "confidence": confidence,
            "source_refs": sorted(matches),
            "observed_projects": sorted(observed_projects),
            "scope_projects": scope_projects,
            "promoted": len(matches) >= minimum,
        }
        candidates.append(record)
        if len(matches) < minimum:
            continue
        promoted.append({
            "id": rid,
            "pattern": applies_to,
            "public_context": context,
            "confidence": confidence,
            "observation_count": len(matches),
            "source_refs": sorted(matches),
            "observed_projects": sorted(observed_projects),
            "scope_projects": scope_projects,
        })

    learned = deepcopy(base_knowledge)
    learned["mode"] = "KNOWLEDGE"
    learned["pack_id"] = f"{base_knowledge.get('pack_id', 'knowledge')}+chat-learned-v0"
    learned["distillation"] = {
        "engine": "knowledge-distiller-v0",
        "input_policy": "allow_public_learning=true only",
        "raw_chat_persisted": False,
        "unique_input_count": len(unique),
        "promoted_rule_count": len(promoted),
    }
    learned["learned_context_rules"] = promoted
    report = {
        "engine": "knowledge-distiller-v0",
        "unique_input_count": len(unique),
        "promoted_rule_count": len(promoted),
        "candidates": candidates,
    }
    return learned, report
