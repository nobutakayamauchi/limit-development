from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

AXES = ("voice_fit", "readability", "factual_fidelity", "task_fit")
AXIS_WEIGHTS = {
    "voice_fit": 1.0,
    "readability": 1.0,
    "factual_fidelity": 1.5,
    "task_fit": 1.5,
}
ALLOWED_FEEDBACK_KEYS = {
    "feedback_id", "rule_id", "surface", "output_id", "ratings", "verdict", "allow_preference_learning"
}
ALLOWED_VERDICTS = {"accept", "revise", "reject"}
STAGE_SHADOW = "SHADOW"
STAGE_ACTIVE = "ACTIVE"
STAGE_DORMANT = "DORMANT"


def load_feedback(path: str | Path):
    items = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"feedback at line {lineno} must be an object")
            unknown = set(item) - ALLOWED_FEEDBACK_KEYS
            if unknown:
                raise ValueError(f"feedback at line {lineno} has unsupported fields: {sorted(unknown)}")
            required = ("feedback_id", "rule_id", "surface", "output_id")
            if any(not str(item.get(k, "")).strip() for k in required):
                raise ValueError(f"feedback at line {lineno} needs feedback_id, rule_id, surface and output_id")
            verdict = item.get("verdict")
            if verdict is not None and verdict not in ALLOWED_VERDICTS:
                raise ValueError(f"feedback at line {lineno} verdict must be accept, revise or reject")
            ratings = item.get("ratings")
            if not isinstance(ratings, dict) or set(ratings) != set(AXES):
                raise ValueError(f"feedback at line {lineno} needs exactly the four rating axes")
            for axis in AXES:
                value = ratings[axis]
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < -2 or value > 2:
                    raise ValueError(f"feedback at line {lineno} rating {axis} must be a number between -2 and 2")
            items.append(item)
    return items


def _weighted_score(ratings):
    numerator = sum(float(ratings[a]) * AXIS_WEIGHTS[a] for a in AXES)
    denominator = sum(AXIS_WEIGHTS.values())
    return round(numerator / denominator, 3)


def _stage(feedback_count, averages, weighted_mean, config):
    minimum = int(config.get("min_feedback_for_active", 3))
    if feedback_count == 0:
        return STAGE_SHADOW
    if averages["factual_fidelity"] < float(config.get("dormant_factual_threshold", 0.0)):
        return STAGE_DORMANT
    if weighted_mean <= float(config.get("dormant_score_threshold", -0.75)):
        return STAGE_DORMANT
    if (
        feedback_count >= minimum
        and weighted_mean >= float(config.get("active_score_threshold", 1.0))
        and averages["factual_fidelity"] >= float(config.get("active_factual_threshold", 1.0))
        and averages["task_fit"] >= float(config.get("active_task_threshold", 0.5))
    ):
        return STAGE_ACTIVE
    return STAGE_SHADOW


def apply_preference_feedback(learned_knowledge, feedback_items, config=None):
    """Attach structured feedback state to chat-learned Knowledge.

    Preference Loop v0 never changes event facts and never copies free-form user
    feedback into Knowledge. It only scores existing learned_context_rules.
    ACTIVE means eligible for explicit promotion; it does not modify CURRENT
    KNOWLEDGE or unattended publication by itself. SHADOW remains visible in the
    experimental candidate so it can earn feedback. DORMANT is retained only in
    the preference catalog/report and is suppressed from generated copy.
    """
    config = config or {}
    rules = {str(x.get("id")): x for x in learned_knowledge.get("learned_context_rules", []) if x.get("id")}
    unique = {}
    seen_outputs = set()
    ignored = []
    for item in feedback_items:
        fid = str(item.get("feedback_id", "")).strip()
        if not fid or fid in unique:
            continue
        if item.get("allow_preference_learning") is not True:
            ignored.append({"feedback_id": fid, "reason": "not_allowlisted"})
            continue
        rid = str(item.get("rule_id", "")).strip()
        if rid not in rules:
            ignored.append({"feedback_id": fid, "reason": "unknown_rule", "rule_id": rid})
            continue
        output_key = (rid, str(item.get("surface", "")).strip(), str(item.get("output_id", "")).strip())
        if output_key in seen_outputs:
            ignored.append({"feedback_id": fid, "reason": "duplicate_output", "rule_id": rid})
            continue
        seen_outputs.add(output_key)
        unique[fid] = item

    by_rule = {rid: [] for rid in rules}
    for item in unique.values():
        by_rule[str(item["rule_id"])].append(item)

    derived = deepcopy(learned_knowledge)
    usable_rules = []
    catalog = []
    report_rules = []
    stage_counts = {STAGE_SHADOW: 0, STAGE_ACTIVE: 0, STAGE_DORMANT: 0}

    for rid, original in rules.items():
        rows = by_rule[rid]
        axis_avg = {}
        for axis in AXES:
            axis_avg[axis] = round(sum(float(x["ratings"][axis]) for x in rows) / len(rows), 3) if rows else 0.0
        scores = [_weighted_score(x["ratings"]) for x in rows]
        weighted_mean = round(sum(scores) / len(scores), 3) if scores else 0.0
        stage = _stage(len(rows), axis_avg, weighted_mean, config)
        stage_counts[stage] += 1

        base_conf = float(original.get("confidence", 0.0))
        delta = max(-0.2, min(0.12, weighted_mean * 0.06)) if rows else 0.0
        adjusted = round(max(0.05, min(0.99, base_conf + delta)), 3)

        surface = {}
        for row in rows:
            name = str(row.get("surface") or "unspecified")
            surface.setdefault(name, []).append(_weighted_score(row["ratings"]))
        surface_scores = {k: round(sum(v) / len(v), 3) for k, v in sorted(surface.items())}

        enriched = deepcopy(original)
        enriched["confidence"] = adjusted
        enriched["preference"] = {
            "stage": stage,
            "feedback_count": len(rows),
            "weighted_score": weighted_mean,
            "axis_averages": axis_avg,
            "surface_scores": surface_scores,
        }
        catalog.append(enriched)
        if stage != STAGE_DORMANT:
            usable_rules.append(enriched)
        report_rules.append({
            "id": rid,
            "stage": stage,
            "feedback_count": len(rows),
            "base_confidence": base_conf,
            "adjusted_confidence": adjusted,
            "weighted_score": weighted_mean,
            "axis_averages": axis_avg,
            "surface_scores": surface_scores,
        })

    derived["pack_id"] = f"{learned_knowledge.get('pack_id', 'knowledge')}+preference-v0"
    derived["learned_context_rules"] = usable_rules
    derived["preference_rule_catalog"] = catalog
    derived["preference_loop"] = {
        "engine": "preference-loop-v0",
        "feedback_policy": "strict structured schema; allow_preference_learning=true only",
        "free_text_persisted": False,
        "feedback_count": len(unique),
        "stage_counts": stage_counts,
        "active_is_auto_published": False,
        "shadow_is_experimental": True,
        "dormant_is_suppressed": True,
        "duplicate_output_counts": False,
    }
    report = {
        "engine": "preference-loop-v0",
        "feedback_count": len(unique),
        "stage_counts": stage_counts,
        "rules": report_rules,
        "ignored": ignored,
    }
    return derived, report
