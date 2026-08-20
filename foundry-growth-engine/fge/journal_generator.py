from __future__ import annotations

from collections import Counter, OrderedDict
from html import escape
from pathlib import Path


def _clean(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


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
    if not isinstance(knowledge, dict):
        return {}
    profiles = knowledge.get("project_profiles", {})
    if not isinstance(profiles, dict):
        return {}
    profile = profiles.get(project) or {}
    return profile if isinstance(profile, dict) else {}


def _project_description(knowledge, project):
    return _clean(_project_profile(knowledge, project).get("public_description") or "")


def _project_goal(knowledge, project):
    """Return only an explicitly public, stable project purpose."""
    return _clean(_project_profile(knowledge, project).get("why_it_matters") or "")


def _representatives(items, limit=3):
    """Choose distinct chronological checkpoints without pretending they are causes."""
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


def generate_journal_body(journal, updates, knowledge=None) -> str:
    """Build a readable daily journal from public Update facts + public Knowledge.

    Stable project aims may come only from `project_profiles.*.why_it_matters`.
    Today's work and progress may come only from already-public Update records.
    The generator does not infer hidden motives, outcomes, causality, private
    context, implementation details, or success that the evidence did not state.
    """
    items = sorted(updates, key=lambda u: u.captured_at)
    if not items:
        return _sentence(getattr(journal, "summary", ""))

    groups = _project_groups(items)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0].captured_at, kv[0]))
    types = Counter(u.type for u in items)
    lead_project, lead_items = ranked[0]

    lines = ["## 今日の中心"]
    if len(items) == 1:
        lines.append(_sentence(items[0].summary or items[0].title))
    else:
        lines.append(_sentence(f"この日は合計{len(items)}件の開発記録があり、最も多かったのは{lead_project}の{len(lead_items)}件でした"))
        description = _project_description(knowledge, lead_project)
        if description:
            lines.append(_sentence(description))

    lead_goal = _project_goal(knowledge, lead_project)
    if lead_goal:
        lines += ["", "## この開発で狙っていること"]
        lines.append(_sentence(lead_goal))
        if len(ranked) > 1:
            lines.append(_sentence(f"今日はその{lead_project}を中心に、ほか{len(ranked) - 1}プロジェクトの変更・検証も並行して記録されています"))

    lines += ["", "## まとまりごとの記録"]
    max_groups = 5
    for project, project_items in ranked[:max_groups]:
        lines.append(f"### {project} — {len(project_items)}件")
        description = _project_description(knowledge, project)
        goal = _project_goal(knowledge, project)
        if description and not (project == lead_project and len(items) > 1):
            lines.append(_sentence(description))
        if goal:
            lines.append(_sentence("狙い: " + goal))
        project_types = Counter(u.type for u in project_items)
        if len(project_types) > 1:
            breakdown = "、".join(f"{name}{count}件" for name, count in sorted(project_types.items()))
            lines.append(_sentence("今日やったことの内訳: " + breakdown))
        representatives = _representatives(project_items)
        for u in representatives:
            time = u.captured_at[11:16] if len(u.captured_at) >= 16 else ""
            prefix = f"{time} " if time else ""
            lines.append(f"- {prefix}{u.title} — {_sentence(u.summary or u.title)}")
        hidden = len(project_items) - len(representatives)
        if hidden > 0:
            lines.append(f"- このまとまりには、ほか{hidden}件の更新があります。")

    if len(ranked) > max_groups:
        other_count = sum(len(rows) for _, rows in ranked[max_groups:])
        other_projects = "、".join(project for project, _ in ranked[max_groups:])
        lines.append(f"### その他 — {other_count}件")
        lines.append(_sentence("対象: " + other_projects))

    lines += ["", "## 一日の広がり"]
    project_names = [project for project, _ in ranked]
    lines.append(_sentence("対象: " + "、".join(project_names)))
    type_text = "、".join(f"{name}{count}件" for name, count in sorted(types.items()))
    lines.append(_sentence("内容: " + type_text))

    lines += ["", "## 今日どこまで進んだか"]
    lead_last = lead_items[-1]
    lines.append(_sentence(f"{lead_project}では、記録上いちばん新しい変更は「{lead_last.title}」です"))
    if lead_last.summary and _clean(lead_last.summary) != _clean(lead_last.title):
        lines.append(_sentence(lead_last.summary))
    if len(ranked) > 1:
        others = "、".join(project for project, _ in ranked[1:4])
        tail = f"同じ日に{others}にも変更・検証の記録があります"
        if len(ranked) > 4:
            tail += f"。そのほか{len(ranked) - 4}プロジェクトにも記録があります"
        lines.append(_sentence(tail))
    if lead_goal:
        lines.append(_sentence("ここでいう『進んだ』は公開Git上で確認できる変更の到達点であり、狙いそのものを達成したという意味ではありません"))

    return "\n".join(lines).strip()


def journal_body_html(body: str) -> str:
    """Render the restricted journal-body format without allowing raw HTML."""
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


def expand_rendered_journals(output_dir, journals, updates, knowledge=None) -> int:
    """Inject expanded bodies into journal pages rendered by the Pages adapter."""
    out = Path(output_dir)
    update_map = {u.id: u for u in updates}
    changed = 0
    for journal in journals:
        path = out / "journal" / f"{journal.date}.html"
        if not path.exists():
            continue
        items = [update_map[i] for i in journal.update_ids if i in update_map]
        body = generate_journal_body(journal, items, knowledge=knowledge)
        lead = f"<p>{escape(journal.summary)}</p>"
        replacement = lead + '<section class="journal-generated">' + journal_body_html(body) + "</section>"
        html = path.read_text(encoding="utf-8")
        if lead not in html:
            continue
        html = html.replace(lead, replacement, 1)
        path.write_text(html, encoding="utf-8")
        changed += 1
    return changed
