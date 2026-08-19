from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from fge.core import load_knowledge
from fge.knowledge_distiller import distill, load_jsonl, load_rules


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--base', default=str(PACKAGE_ROOT / 'config/knowledge.limit-development.json'))
    ap.add_argument('--rules', default=str(PACKAGE_ROOT / 'config/distiller.rules.json'))
    ap.add_argument('--output', required=True)
    ap.add_argument('--report', required=True)
    args = ap.parse_args()

    entries = load_jsonl(args.input)
    base = load_knowledge(args.base)
    rules = load_rules(args.rules)
    learned, report = distill(entries, base, rules)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(learned, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'engine': report['engine'],
        'input_count': report['unique_input_count'],
        'promoted_rule_count': report['promoted_rule_count'],
        'knowledge_output': args.output,
        'report_output': args.report,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
