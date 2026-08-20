from __future__ import annotations

from collections import Counter, OrderedDict
from html import escape
from pathlib import Path
import re

from .daily_intent import resolve_daily_intent
from .journal_generator import _project_description, _project_goal, _representatives, journal_body_html


def _clean(text):
    return " ".join(str(text or "").split()).strip()


def _sentence(text):
    text = _clean(text)
    if not text:
        return ""
    return text if text.endswith(("。", "！", "？", "!", "?")) else text + "。"


def _summary_meaning(update):
    """Use existing public summary context as the reader-facing meaning."""
    parts = [x.strip() for x in re.split(r"(?<=。)", _clean(update.summary or update.title)) if x.strip()]
    if len(parts) > 1:
        title_key = re.sub(r"[\s。・\-—]", "", _clean(update.title))
        first_key = re.sub(r"[\s。・\-—]", "", parts[0])
        if title_key and (title_key in first_key or first_key in title_key):
            parts = parts[1:]
    return _clean(" ".join(parts)) or _clean(update.summary or update.title)


def generate_reader_body(journal, updates, knowledge=None, daily_intents=None):
    items = sorted(updates, key=lambda u: u.captured_at)
    if not items:
        return _sentence(getattr(journal, "summary", ""))

    groups = OrderedDict()
    for item in items:
        groups.setdefault(item.project, []).append(item)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0].captured_at, kv[0]))
    lead_project, lead_items = ranked[0]
    intent = resolve_daily_intent(daily_intents or [], journal.date, lead_project, knowledge=knowledge)
    goal = _project_goal(knowledge, lead_project)

    lines = []
    if intent:
        lines += ["## 今日の狙い", _sentence(intent["intent"])]
    else:
        lines += ["## 今日の中心", _sentence(_project_description(knowledge, lead_project) or lead_items[-1].summary)]
    if len(items) > 1:
        lines.append(_sentence(f"記録は{len(items)}件。{lead_project}を中心に進みました"))

    if goal:
        lines += ["", "## この開発の目的", _sentence(goal)]

    lines += ["", "## 今日やったこと"]
    for project, project_items in ranked[:5]:
        lines.append(f"### {project}")
        if project != lead_project:
            description = _project_description(knowledge, project)
            project_goal = _project_goal(knowledge, project)
            if description:
                lines.append(_sentence(description))
            if project_goal:
                lines.append(_sentence("目的: " + project_goal))
        counts = Counter(x.type for x in project_items)
        breakdown = "、".join(f"{name}{count}件" for name, count in sorted(counts.items()))
        lines.append(_sentence(f"記録: {len(project_items)}件" + (f"（{breakdown}）" if breakdown else "")))
        reps = _representatives(project_items)
        for item in reps:
            time = item.captured_at[11:16] if len(item.captured_at) >= 16 else ""
            label = f"{item.type}: " if _clean(item.type) else ""
            lines.append(f"- {time} {label}{_sentence(_summary_meaning(item))}".strip())
        hidden = len(project_items) - len(reps)
        if hidden > 0:
            lines.append(f"- ほか{hidden}件は、下の詳細記録に残しています。")

    if len(ranked) > 5:
        rest = "、".join(name for name, _ in ranked[5:])
        count = sum(len(rows) for _, rows in ranked[5:])
        lines += ["### その他", _sentence(f"{rest}にも合計{count}件の記録があります")]

    lines += ["", "## 一日の広がり"]
    lines.append(_sentence("触ったプロジェクト: " + "、".join(name for name, _ in ranked)))
    all_types = Counter(x.type for x in items)
    lines.append(_sentence("変更の内訳: " + "、".join(f"{name}{count}件" for name, count in sorted(all_types.items()))))

    latest = lead_items[-1]
    lines += ["", "## 今日どこまで進んだか"]
    lines.append(_sentence(f"{lead_project}の最新記録は「{latest.title}」です"))
    lines.append(_sentence(_summary_meaning(latest)))
    if len(ranked) > 1:
        lines.append(_sentence("同じ日に" + "、".join(name for name, _ in ranked[1:4]) + "にも変更・検証の記録があります"))
    return "\n".join(lines).strip()


def expand_reader_journals(output_dir, journals, updates, knowledge=None, daily_intents=None):
    out = Path(output_dir)
    update_map = {u.id: u for u in updates}
    changed = 0
    for journal in journals:
        path = out / "journal" / f"{journal.date}.html"
        if not path.exists():
            continue
        items = [update_map[i] for i in journal.update_ids if i in update_map]
        body = generate_reader_body(journal, items, knowledge=knowledge, daily_intents=daily_intents)
        lead = f"<p>{escape(journal.summary)}</p>"
        replacement = lead + '<section class="journal-generated">' + journal_body_html(body) + "</section>"
        html = path.read_text(encoding="utf-8")
        if lead not in html:
            continue
        path.write_text(html.replace(lead, replacement, 1), encoding="utf-8")
        changed += 1
    return changed
