from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def key(item):
    return (str(item.get('captured_at', ''))[:13], str(item.get('project', '')), str(item.get('type', '')))


def esc(text):
    return str(text or '').replace('|', '\\|').replace('\n', ' ')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plain', required=True)
    ap.add_argument('--current', required=True)
    ap.add_argument('--learned', required=True)
    ap.add_argument('--current-human', required=True)
    ap.add_argument('--learned-human', required=True)
    ap.add_argument('--distill-report', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    modes = {
        'PLAIN': {key(x): x for x in load(args.plain)},
        'CURRENT': {key(x): x for x in load(args.current)},
        'CHAT-LEARNED': {key(x): x for x in load(args.learned)},
        'CURRENT + /human': {key(x): x for x in load(args.current_human)},
        'CHAT-LEARNED + /human': {key(x): x for x in load(args.learned_human)},
    }
    report = load(args.distill_report)
    keys = sorted(set().union(*(set(m) for m in modes.values())), reverse=True)
    lines = [
        '# FGE presentation comparison: PLAIN / KNOWLEDGE / CHAT / /human',
        '',
        f"Knowledge Distiller: `{report.get('engine')}` / promoted rules: **{report.get('promoted_rule_count', 0)}** / safe inputs: **{report.get('unique_input_count', 0)}**",
        '',
        '`/human` is an editing pass only. It may shorten, reorder and connect existing public-safe facts/context; it is not allowed to invent event facts.',
        '',
    ]

    shown = 0
    for k in keys:
        rows = {name: data.get(k) for name, data in modes.items()}
        if not all(rows.values()):
            continue
        pairs = {(x.get('title'), x.get('summary')) for x in rows.values()}
        if len(pairs) == 1:
            continue
        shown += 1
        lines += [
            f"## {k[0]} / {esc(k[1])} / {esc(k[2])}",
            '',
            '| MODE | TITLE | SUMMARY |',
            '|---|---|---|',
        ]
        for name in modes:
            row = rows[name]
            lines.append(f"| {esc(name)} | {esc(row.get('title'))} | {esc(row.get('summary'))} |")
        lines.append('')
        if shown >= 12:
            break

    if shown == 0:
        lines += ['No aligned output differences were found in this run.', '']
    Path(args.output).write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'compared_groups': len(keys), 'shown_differences': shown, 'output': args.output}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
