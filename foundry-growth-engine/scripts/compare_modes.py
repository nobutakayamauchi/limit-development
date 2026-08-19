from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected list: {path}")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plain", required=True)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    plain = {x.get("source_id"): x for x in load(args.plain) if x.get("source_id")}
    knowledge = {x.get("source_id"): x for x in load(args.knowledge) if x.get("source_id")}
    ids = [sid for sid in knowledge if sid in plain]

    lines = [
        "# FGE PLAIN / KNOWLEDGE comparison",
        "",
        "Same Evidence, two replaceable presentation modes.",
        "",
        "- **PLAIN**: operator knowledge removed; regression baseline.",
        "- **KNOWLEDGE**: public context / vocabulary / project meaning added.",
        "- Event facts must remain grounded in the same Evidence.",
        "",
    ]
    changed = 0
    for sid in ids[: max(1, args.limit)]:
        p, k = plain[sid], knowledge[sid]
        is_changed = (p.get("title"), p.get("summary"), p.get("project")) != (k.get("title"), k.get("summary"), k.get("project"))
        changed += int(is_changed)
        lines.extend([
            f"## {sid[:12]} {'CHANGED' if is_changed else 'SAME'}",
            "",
            f"**PLAIN / {p.get('project','')}**  ",
            f"{p.get('title','')}  ",
            f"{p.get('summary','')}",
            "",
            f"**KNOWLEDGE / {k.get('project','')}**  ",
            f"{k.get('title','')}  ",
            f"{k.get('summary','')}",
            "",
        ])
    lines.insert(8, f"Compared common public updates: {len(ids)} / changed in preview: {changed}")
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
