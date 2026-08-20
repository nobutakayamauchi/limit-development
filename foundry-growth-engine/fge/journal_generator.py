from __future__ import annotations

from collections import Counter, OrderedDict
from html import escape
from pathlib import Path
import re

from .daily_intent import resolve_daily_intent


def _clean(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _norm_project(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]+", " ", _clean(text)).casefold()


def _sentence(text: str) -> str:
    text = _clean(text)
    if not text:
        return ""
    return text if text.endswith(("。", "！", "？", "!", "?")) else text + "。"


def _project_groups(items):
    groups = OrderedDict()
    for item in items:
        groups.setdefault(item.project, []).append(item)
    return groups


def _project_profile(knowledge, project):
    """Resolve only identity-safe project profiles for JOURNAL purpose text.

    The general Knowledge alias table is also used to classify commit text and
    can contain broad semantic patterns. JOURNAL purpose/intent needs stricter
    entity identity, so alias fallback is limited to punctuation/spacing variants
    such as `WebAI-Bridge` -> `WebAI Bridge`. If identity is uncertain, omit the
    purpose rather than attaching the wrong product story.
    """
    if not isinstance(knowledge, dict):
        return {}
    profiles = knowledge.get("project_profiles", {})
    if not isinstance(profiles, dict):
        return {}
    profile = profiles.get(project)
    if isinstance(profile, dict):
        return profile

    raw = str(project or "")
    normalized = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]+", " ", raw).strip()
    raw_norm = _norm_project(raw)
    for alias in knowledge.get("project_aliases", []):
        if not isinstance(alias, dict):
            continue
        pattern = str(alias.get("pattern") or "")
        target = str(alias.get("project") or "")
        if not pattern or target not in profiles:
            continue
        if _norm_project(target) != raw_norm:
            continue
        try:
            matched = re.search(pattern, raw, flags=re.I) or re.search(pattern, normalized, flags=re.I)
        except re.error:
            matched = None
        if matched and isinstance(profiles.get(target), dict):
            return profiles[target]
    return {}


def _project_description(knowledge, project):
    return _clean(_project_profile(knowledge, project).get("public_description") or "")


def _project_goal(knowledge, project):
    return _clean(_project_profile(knowledge, project).get("why_it_matters") or "")


def _representatives(items, limit=3):
    if not items:
        return []
    unique = []
    seen = set()
    for item in items:
        key = (_clean(item.title), _clean(item.summary))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    if len(unique) <= limit:
        return unique
    indexes = [0, len(unique) // 2, len(unique) - 1]
    return [unique[i] for i in indexes[:limit]]


def generate_journal_body(journal, updates, knowledge=None, daily_intents=None) -> str:
    """Journal Generator v0.3: separate today's intent, facts and stable purpose.

    TODAY'S INTENT = explicitly approved /goal or Chat Observation for this date.
    ACTUAL WORK = already-public Git-derived Update records.
    PROJECT PURPOSE = replaceable public Knowledge (`why_it_matters`).

    These sources are deliberately kept separate. The generator never infers a
    daily goal from commits and never treats a stable project purpose as proof of
    what the operator intended on a particular day.
    """
    items = sorted(updates, key=lambda u: u.captured_at)
    if not items:
        return _sentence(getattr(journal, "summary", ""))

    groups = _project_groups(items)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0].captured_at, kv[0]))
    types = Counter(u.type for u in items)
    lead_project, lead_items = ranked[0]
    intents = daily_intents or []
    lead_intent = resolve_daily_intent(intents, journal.date, lead_project, knowledge=knowledge)
    lead_goal = _project_goal(knowledge, lead_project)

    lines = ["## 今日の中心"]
    if len(items) == 1:
        lines.append(_sentence(items[0].summary or items[0].title))
    else:
        lines.append(_sentence(f"この日は合計{len(items)}件の開発記録があり、最も多かったのは{lead_project}の{len(lead_items)}件でした"))
        description = _project_description(knowledge, lead_project)
        if description:
            lines.append(_sentence(description))

    if lead_intent:
        lines += ["", "## 今日の狙い"]
        lines.append(_sentence(lead_intent["intent"]))
        source_label = "/goal" if lead_intent.get("source_type") == "goal" else "承認済みChat Observation"
        lines.append(_sentence(f"この狙いは{source_label}として公開利用を承認した記録から入れています"))

    if lead_goal:
        lines += ["", "## この開発の目的"]
        lines.append(_sentence(lead_goal))
        lines.append(_sentence("これはその日の推測ではなく、公開ナレッジに置いた継続的なプロジェクト目的です"))

    lines += ["", "## 今日やったこと"]
    max_groups = 5
    for project, project_items in ranked[:max_groups]:
        lines.append(f"### {project} — {len(project_items)}件")
        description = _project_description(knowledge, project)
        project_intent = resolve_daily_intent(intents, journal.date, project, knowledge=knowledge)
        goal = _project_goal(knowledge, project)
        if description and not (project == lead_project and len(items) > 1):
            lines.append(_sentence(description))
        if project != lead_project and project_intent:
            lines.append(_sentence("今日の狙い: " + project_intent["intent"]))
        if project != lead_project and goal:
            lines.append(_sentence("継続的な目的: " + goal))
        project_types = Counter(u.type for u in project_items)
        if len(project_types) > 1:
            breakdown = "、".join(f"{name}{count}件" for name, count in sorted(project_types.items()))
            lines.append(_sentence("実際の変更内訳: " + breakdown))
        representatives = _representatives(project_items)
        for u in representatives:
            time = u.captured_at[11:16] if len(u.captured_at) >= 16 else ""
            prefix = f"{time} " if time else ""
            lines.append(f"- {prefix}{u.title} — {_sentence(u.summary or u.title)}")
        hidden = len(project_items) - len(representatives)
        if hidden > 0:
            lines.append(f"- このまとまりには、ほか{hidden}件の公開Git由来の更新があります。")

    if len(ranked) > max_groups:
        other_count = sum(len(rows) for _, rows in ranked[max_groups:])
        other_projects = "、".join(project for project, _ in ranked[max_groups:])
        lines.append(f"### その他 — {other_count}件")
        lines.append(_sentence("対象: " + other_projects))

    lines += ["", "## 一日の広がり"]
    project_names = [project for project, _ in ranked]
    lines.append(_sentence("対象: " + "、".join(project_names)))
    type_text = "、".join(f"{name}{count}件" for name, count in sorted(types.items()))
    lines.append(_sentence("公開Gitで確認できた内容: " + type_text))

    lines += ["", "## 今日どこまで進んだか"]
    lead_last = lead_items[-1]
    lines.append(_sentence(f"{lead_project}では、公開Git上でいちばん新しい到達点は「{lead_last.title}」です"))
    if lead_last.summary and _clean(lead_last.summary) != _clean(lead_last.title):
        lines.append(_sentence(lead_last.summary))
    if lead_intent:
        lines.append(_sentence("今日の狙いに対して、ここまでが現時点でGitから確認できる実作業です。狙いを完全に達成したという判定はしていません"))
    elif lead_goal:
        lines.append(_sentence("ここでいう到達点は公開Git上の観測結果であり、プロジェクト目的そのものを達成したという意味ではありません"))
    if len(ranked) > 1:
        others = "、".join(project for project, _ in ranked[1:4])
        tail = f"同じ日に{others}にも変更・検証の記録があります"
        if len(ranked) > 4:
            tail += f"。そのほか{len(ranked) - 4}プロジェクトにも記録があります"
        lines.append(_sentence(tail))

    return "\n".join(lines).strip()


def journal_body_html(body: str) -> str:
    chunks = []
    in_list = False
    for raw in str(body or "").splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                chunks.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                chunks.append("</ul>")
                in_list = False
            chunks.append(f'<h3 class="journal-cluster">{escape(line[4:])}</h3>')
        elif line.startswith("## "):
            if in_list:
                chunks.append("</ul>")
                in_list = False
            chunks.append(f'<h2 class="journal-section">{escape(line[3:])}</h2>')
        elif line.startswith("- "):
            if not in_list:
                chunks.append('<ul class="journal-flow">')
                in_list = True
            chunks.append(f"<li>{escape(line[2:])}</li>")
        else:
            if in_list:
                chunks.append("</ul>")
                in_list = False
            chunks.append(f'<p class="journal-body">{escape(line)}</p>')
    if in_list:
        chunks.append("</ul>")
    return "".join(chunks)


def expand_rendered_journals(output_dir, journals, updates, knowledge=None, daily_intents=None) -> int:
    out = Path(output_dir)
    update_map = {u.id: u for u in updates}
    changed = 0
    for journal in journals:
        path = out / "journal" / f"{journal.date}.html"
        if not path.exists():
            continue
        items = [update_map[i] for i in journal.update_ids if i in update_map]
        body = generate_journal_body(journal, items, knowledge=knowledge, daily_intents=daily_intents)
        lead = f"<p>{escape(journal.summary)}</p>"
        replacement = lead + '<section class="journal-generated">' + journal_body_html(body) + "</section>"
        html = path.read_text(encoding="utf-8")
        if lead not in html:
            continue
        html = html.replace(lead, replacement, 1)
        path.write_text(html, encoding="utf-8")
        changed += 1
    return changed
