from __future__ import annotations
from dataclasses import replace

COUNT_TITLES = {
    '機能追加': '{project}に{count}件の機能を追加',
    '機能変更': '{project}を{count}箇所改善',
    '機能削除': '{project}の機能を{count}件整理',
    '研究・検証': '{project}で{count}件を検証',
    '方針変更': '{project}の方針を{count}件更新',
}

def compact_hourly(updates, contextual=False):
    """Collapse commit-level noise into public hourly units.

    PLAIN keeps the original count-oriented behavior. KNOWLEDGE mode may set
    contextual=True so a useful human explanation is not overwritten by a
    generic "N changes" sentence during compaction.
    """
    groups = {}
    for u in updates:
        hour = u.captured_at[:13]
        groups.setdefault((hour, u.project, u.type), []).append(u)

    out = []
    for key, items in groups.items():
        items = sorted(items, key=lambda x: x.captured_at, reverse=True)
        base = max(items, key=lambda x: (x.article_candidate, x.article_score, x.captured_at))
        if len(items) == 1:
            out.append(base)
            continue
        title = base.title
        summary = base.summary
        if not base.article_candidate:
            if contextual:
                summary = f'{base.summary} 同じ1時間内の関連変更{len(items)-1}件も、この更新にまとめています。'
            else:
                title = COUNT_TITLES.get(base.type, '{project}で{count}件の更新').format(project=base.project, count=len(items))
                summary = f'{base.project}で同じ1時間内に行った{len(items)}件の変更を、ひとつの更新情報としてまとめました。'
        else:
            summary = f'{base.summary} 同じ1時間内の関連変更{len(items)-1}件もまとめています。'
        tags = sorted({tag for item in items for tag in item.tags})
        refs = ','.join(x.raw_evidence_ref for x in items if x.raw_evidence_ref)
        out.append(replace(base, title=title, summary=summary, tags=tags, raw_evidence_ref=refs, article_score=max(x.article_score for x in items), article_candidate=any(x.article_candidate for x in items)))
    return sorted(out, key=lambda x: x.captured_at, reverse=True)
