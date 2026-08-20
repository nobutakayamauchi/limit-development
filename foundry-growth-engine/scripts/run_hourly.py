from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from fge.adapters.github_input import GitHubGitAdapter
from fge.adapters.work_record_input import WorkRecordFileAdapter
from fge.adapters.pages_output import render_site
from fge.compact import compact_hourly
from fge.human_editor import humanize_updates, humanize_journals
from fge.core import (
    INTENT_RECORD_ONLY,
    build_update,
    build_article,
    build_journals,
    load_knowledge,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', action='append', dest='repos', help='Repository path. Repeat to aggregate multiple repositories.')
    ap.add_argument('--knowledge', default=str(PACKAGE_ROOT/'config/knowledge.limit-development.json'))
    ap.add_argument('--plain', action='store_true', help='Ignore operator knowledge and use the pinned PLAIN pack.')
    ap.add_argument('--human', action='store_true', help='Run the conservative /human editing pass before ARTICLE/JOURNAL/SNS generation.')
    ap.add_argument('--output', default=str(PACKAGE_ROOT/'site'))
    ap.add_argument('--lookback-days', type=int, default=30)
    ap.add_argument('--work-record-dir', default='.fge/records')
    ap.add_argument('--git-only', action='store_true', help='Use only Git evidence and suppress ARTICLE generation. Intended for safe automatic publication from already-public repositories.')
    args = ap.parse_args()

    if args.git_only and args.human:
        ap.error('--human is review-only in v0 and cannot be combined with --git-only unattended publication')

    repos = args.repos or ['.']
    knowledge_path = PACKAGE_ROOT/'config/knowledge.plain.json' if args.plain else Path(args.knowledge) if args.knowledge else None
    knowledge = load_knowledge(str(knowledge_path)) if knowledge_path else {}
    base_mode = 'PLAIN' if args.plain or knowledge.get('mode') != 'KNOWLEDGE' else 'KNOWLEDGE'
    generation_mode = f'{base_mode}+HUMAN' if args.human else base_mode

    git_evidence = []
    for repo in repos:
        git_evidence.extend(GitHubGitAdapter(repo, args.lookback_days).collect())

    work_record_evidence = [] if args.git_only else WorkRecordFileAdapter(repos[0], args.work_record_dir).collect()
    evidence = git_evidence + work_record_evidence

    seen = set(); raw_updates = []; by_source = {}; record_only = 0
    for ev in evidence:
        if ev.source_id in seen: continue
        seen.add(ev.source_id); by_source[ev.source_id] = ev
        if ev.explicit_intent == INTENT_RECORD_ONLY:
            record_only += 1
            continue
        raw_updates.append(build_update(ev, knowledge))

    updates = compact_hourly(raw_updates, contextual=(base_mode == 'KNOWLEDGE'))
    if args.human:
        updates = humanize_updates(updates, by_source, knowledge)

    articles = [] if args.git_only else [build_article(u, by_source[u.source_id], knowledge) for u in updates if u.article_candidate]
    journals = build_journals(updates)
    if args.human:
        journals = humanize_journals(journals, updates, knowledge)

    timezone_name = knowledge.get('organization', {}).get('timezone', 'UTC')
    checked = datetime.now(ZoneInfo(timezone_name)).isoformat(timespec='minutes')
    render_site(args.output, updates, articles, journals, checked)

    metadata = {
        'mode': generation_mode,
        'knowledge_pack': Path(knowledge_path).name if knowledge_path else 'NONE',
        'knowledge_schema': knowledge.get('schema_version', 'plain-v0'),
        'human_editor': 'human-editor-v0' if args.human else 'OFF',
        'checked_at': checked,
        'repositories': [str(Path(r)) for r in repos],
        'git_only': args.git_only,
        'evidence_count': len(evidence),
        'public_update_count': len(updates),
        'article_candidates': len(articles),
        'journal_days': len(journals),
    }
    meta_path = Path(args.output)/'data/generation.json'
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'checked_at': checked,
        'repository_count': len(repos),
        'evidence_count': len(evidence),
        'git_evidence_count': len(git_evidence),
        'work_record_count': len(work_record_evidence),
        'record_only_count': record_only,
        'raw_update_count': len(raw_updates),
        'public_update_count': len(updates),
        'article_candidates': len(articles),
        'journal_days': len(journals),
        'generation_mode': generation_mode,
        'human_editor': metadata['human_editor'],
        'knowledge_pack': metadata['knowledge_pack']
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
