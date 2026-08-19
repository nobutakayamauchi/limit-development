from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from fge.adapters.github_input import GitHubGitAdapter
from fge.adapters.pages_output import render_site
from fge.compact import compact_hourly
from fge.core import build_update, build_article, build_journals, load_knowledge

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.')
    ap.add_argument('--knowledge', default=str(PACKAGE_ROOT/'config/knowledge.limit-development.json'))
    ap.add_argument('--output', default=str(PACKAGE_ROOT/'site'))
    ap.add_argument('--lookback-days', type=int, default=30)
    args = ap.parse_args()

    knowledge = load_knowledge(args.knowledge) if args.knowledge else {}
    evidence = GitHubGitAdapter(args.repo, args.lookback_days).collect()
    seen = set(); raw_updates = []; by_source = {}
    for ev in evidence:
        if ev.source_id in seen: continue
        seen.add(ev.source_id); by_source[ev.source_id] = ev
        raw_updates.append(build_update(ev, knowledge))

    updates = compact_hourly(raw_updates)
    articles = [build_article(u, by_source[u.source_id], knowledge) for u in updates if u.article_candidate]
    journals = build_journals(updates)
    timezone_name = knowledge.get('organization', {}).get('timezone', 'UTC')
    checked = datetime.now(ZoneInfo(timezone_name)).isoformat(timespec='minutes')
    render_site(args.output, updates, articles, journals, checked)
    print(json.dumps({
        'checked_at': checked,
        'evidence_count': len(evidence),
        'raw_update_count': len(raw_updates),
        'public_update_count': len(updates),
        'article_candidates': len(articles),
        'journal_days': len(journals),
        'knowledge_pack': Path(args.knowledge).name if args.knowledge else 'PLAIN'
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
