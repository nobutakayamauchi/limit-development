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


def _unique(items):
    out = []
    seen = set()
    for item in items:
        key = _clean(item)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _project_groups(items):
    groups = OrderedDict()
    for item in items:
        groups.setdefault(item.project, []).append(item)
    return groups


def _project_context(knowledge, project):
    if not isinstance(knowledge, dict):
        return ""
    profiles = knowledge.get("project_profiles", {})
    if not isinstance(profiles, dict):
        return ""
    profile = profiles.get(project) or {}
    if not isinstance(profile, dict):
        return ""
    return _clean(profile.get("public_description") or profile.get("why_it_matters") or "")


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
    """Build a readable daily journal body from already-public Update facts.

    v0.1 groups a busy day into project-sized chapters instead of copying a long
    chronological log. It may use an already-public project description from the
    replaceable Knowledge pack, but it does not infer motives, outcomes, private
    context, causality, or implementation details. The underlying UPDATE cards
    remain the detailed source beneath the generated narrative.
    """
    items = sorted(updates, key=lambda u: u.captured_at)
    if not items:
        return _sentence(getattr(journal, "summary", ""))

    groups = _project_groups(items)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0].captured_at, kv[0]))
    types = Counter(u.type for u in items)

    lines = ["## 今日の中心"]
    if len(items) == 1:
        lines.append(_sentence(items[0].summary or items[0].title))
    else:
        lead_project, lead_items = ranked[0]
        lines.append(_sentence(f"この日は合計{len(items)}件の開発記録があり、最も多かったのは{lead_project}の{len(lead_items)}件でした"))
        context = _project_context(knowledge, lead_project)
        if context:
            lines.append(_sentence(context))

    lines += ["", "## まとまりごとの記録"]
    max_groups = 5
    for project, project_items in ranked[:max_groups]:
        lines.append(f"### {project} — {len(project_items)}件")
        context = _project_context(knowledge, project)
        if context and not (ranked and project == ranked[0][0] and len(items) > 1):
            lines.append(_sentence(context))
        project_types = Counter(u.type for u in project_items)
        if len(project_types) > 1:
            breakdown = "、".join(f"{name}{count}件" for name, count in sorted(project_types.items()))
            lines.append(_sentence("内訳: " + breakdown))
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

    lines += ["", "## 今日の結論"]
    if len(ranked) == 1:
        project, rows = ranked[0]
        lines.append(_sentence(f"この日の記録は{project}に集中し、{len(rows)}件の変更・検証としてまとまりました"))
    else:
        lead_project, lead_items = ranked[0]
        others = "、".join(project for project, _ in ranked[1:4])
        conclusion = f"この日は{lead_project}の{len(lead_items)}件を中心に、{others}にも開発が広がりました"
        if len(ranked) > 4:
            conclusion += f"。そのほか{len(ranked) - 4}プロジェクトにも記録があります"
        lines.append(_sentence(conclusion))

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
