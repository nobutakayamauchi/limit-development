from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from fge.preference_loop import apply_preference_feedback, load_feedback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--knowledge', required=True)
    ap.add_argument('--feedback', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--report', required=True)
    args = ap.parse_args()

    knowledge = json.loads(Path(args.knowledge).read_text(encoding='utf-8'))
    feedback = load_feedback(args.feedback)
    derived, report = apply_preference_feedback(knowledge, feedback)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(derived, ensure_ascii=False, indent=2), encoding='utf-8')
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'engine': report['engine'],
        'feedback_count': report['feedback_count'],
        'stage_counts': report['stage_counts'],
        'output': args.output,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
