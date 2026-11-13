"""Replace the rolling journal output without deleting the static fallback."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def prepare_journal_publish(bundle: Path, root: Path = ROOT) -> None:
    template = (root / "foundry-growth-engine/templates/journal-index.html").read_bytes()
    fallback_names = set(re.findall(rb'href="(\d{4}-\d{2}-\d{2}\.html)"', template))
    if not fallback_names:
        raise ValueError("journal template must retain its static fallback links")
    target = root / "journal"
    # Read every required input before replacing any published files.
    fallback = {name.decode(): (target / name.decode()).read_bytes() for name in fallback_names}
    journals = json.loads((bundle / "data/journals.json").read_text(encoding="utf-8"))
    if not isinstance(journals, list):
        raise ValueError("journals.json must be a list")
    with tempfile.TemporaryDirectory() as td:
        staged = Path(td) / "journal"
        staged.mkdir()
        for journal in journals:
            day = journal["date"]
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError(f"invalid journal date: {day}")
            name = f"{day}.html"
            html = (bundle / "journal" / name).read_text(encoding="utf-8")
            # Older reviewed bundles used a path outside the repository's Pages root.
            html = html.replace('href="../../archive/"', 'href="../archive/"')
            (staged / name).write_text(html, encoding="utf-8")
        for name, content in fallback.items():
            (staged / name).write_bytes(content)
        (staged / "index.html").write_bytes(template)
        shutil.rmtree(target)
        shutil.copytree(staged, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    prepare_journal_publish(args.bundle)
