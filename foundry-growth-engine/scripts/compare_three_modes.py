from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def key(item):
    captured = str(item.get('captured_at', ''))[:13]
    return (captured, str(item.get('project', '')), str(item.get('type', '')))


def esc(text):
    return str(text or '').replace('|', '\\|').replace('\n', ' ')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plain', required=True)
    ap.add_argument('--current', required=True)
    ap.add_argument('--learned', required=True)
    ap.add_argument('--distill-report', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    modes = {
        'PLAIN': {key(x): x for x in load(args.plain)},
        'CURRENT KNOWLEDGE': {key(x): x for x in load(args.current)},
        'CHAT-LEARNED': {key(x): x for x in load(args.learned)},
    }
    report = load(args.distill_report)
    keys = sorted(set().union(*(set(m) for m in modes.values())), reverse=True)

    lines = [
        '# PLAIN / CURRENT KNOWLEDGE / CHAT-LEARNED',
        '',
        f"Knowledge Distiller: `{report.get('engine')}` / promoted rules: **{report.get('promoted_rule_count', 0)}** / safe inputs: **{report.get('unique_input_count', 0)}**",
        '',
        'The same Git evidence is rendered three ways. PLAIN is the pinned baseline, CURRENT KNOWLEDGE is the normal operator pack, and CHAT-LEARNED adds only promoted context distilled from allowlisted chat observations.',
        '',
    ]

    shown = 0
    for k in keys:
        p = modes['PLAIN'].get(k)
        c = modes['CURRENT KNOWLEDGE'].get(k)
        l = modes['CHAT-LEARNED'].get(k)
        if not (p and c and l):
            continue
        if p.get('title') == c.get('title') == l.get('title') and p.get('summary') == c.get('summary') == l.get('summary'):
            continue
        shown += 1
        lines += [
            f"## {k[0]} / {esc(k[1])} / {esc(k[2])}",
            '',
            '| MODE | TITLE | SUMMARY |',
            '|---|---|---|',
            f"| PLAIN | {esc(p.get('title'))} | {esc(p.get('summary'))} |",
            f"| CURRENT | {esc(c.get('title'))} | {esc(c.get('summary'))} |",
            f"| CHAT-LEARNED | {esc(l.get('title'))} | {esc(l.get('summary'))} |",
            '',
        ]
        if shown >= 12:
            break

    if shown == 0:
        lines += ['No aligned output differences were found in this run.', '']

    Path(args.output).write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'compared_groups': len(keys), 'shown_differences': shown, 'output': args.output}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
