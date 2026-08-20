from __future__ import annotations

from collections import Counter


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


def generate_journal_body(journal, updates) -> str:
    """Build a readable daily journal body from already-public Update facts.

    This layer is deliberately conservative: it does not infer motives, results,
    emotions, or implementation details. It only reorganizes titles, summaries,
    project/type distribution and chronological order already present upstream.
    Knowledge and /human wording therefore remain the source of meaning; this
    generator only gives that material enough room to become an actual journal.
    """
    items = sorted(updates, key=lambda u: u.captured_at)
    if not items:
        return _sentence(getattr(journal, "summary", ""))

    projects = _unique([u.project for u in items])
    types = Counter(u.type for u in items)
    summaries = _unique([u.summary for u in items])

    lines = []
    lines.append("## 今日やったこと")
    if len(items) == 1:
        lines.append(_sentence(summaries[0] if summaries else items[0].title))
    else:
        lead = summaries[0] if summaries else items[0].title
        lines.append(_sentence(lead))
        lines.append(_sentence(f"この日は合計{len(items)}件の開発記録がありました"))

    lines.append("")
    lines.append("## 開発の流れ")
    max_detail = 10 if len(items) >= 8 else len(items)
    for u in items[:max_detail]:
        time = u.captured_at[11:16] if len(u.captured_at) >= 16 else ""
        prefix = f"{time} " if time else ""
        detail = _sentence(u.summary or u.title)
        lines.append(f"- {prefix}{u.title} — {detail}")
    if len(items) > max_detail:
        lines.append(f"- ほか{len(items) - max_detail}件の更新を記録しています。")

    if len(projects) > 1 or len(types) > 1:
        lines.append("")
        lines.append("## 今日の広がり")
        if projects:
            lines.append(_sentence("対象: " + "、".join(projects)))
        if types:
            type_text = "、".join(f"{name} {count}件" for name, count in sorted(types.items()))
            lines.append(_sentence("内容: " + type_text))

    lines.append("")
    lines.append("## 今日の結論")
    if len(summaries) >= 2:
        lines.append(_sentence(summaries[-1]))
    else:
        lines.append(_sentence(summaries[0] if summaries else items[-1].title))

    return "\n".join(lines).strip()
