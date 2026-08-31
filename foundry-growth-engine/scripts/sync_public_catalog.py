#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

SALES_BASE = "https://nobutakayamauchi.github.io/sales-catalog/"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def normalize_sales_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return SALES_BASE + value.lstrip("./")


def default_short(name: str) -> str:
    clean = "".join(ch for ch in name if ch.isalnum())
    return (clean[:1] or "•").upper()


def sales_item(product: dict, editorial: dict) -> dict:
    pid = str(product.get("id", "")).strip()
    name = str(product.get("name") or pid).strip()
    item = {
        "id": pid,
        "name": name.upper() if len(name) < 30 else name,
        "short": default_short(name),
        "kind": "PRODUCT / PRODUCTION" if product.get("type") == "software" else "SERVICE / PRODUCTION",
        "cats": ["production", "product"],
        "killer": str(product.get("summary") or "販売中です。"),
        "desc": str(product.get("summary") or ""),
        "definition": str(product.get("summary") or ""),
        "url": normalize_sales_url(product.get("overview_url", "")),
        "salesUrl": normalize_sales_url(product.get("sales_url", "")),
        "repo": str(product.get("canonical_repo") or ""),
        "status": str(product.get("status") or ""),
        "priority": 999,
        "source": "sales-catalog"
    }
    item.update(editorial.get(pid, {}))
    return item


def manifest_items(repo_roots):
    found = []
    for root in repo_roots:
        manifest = Path(root) / ".foundry" / "public.json"
        data = read_json(manifest, None)
        if not data:
            continue
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("status", "public") not in {"public", "for_sale", "published", "research"}:
                continue
            if not entry.get("id") or not entry.get("name"):
                continue
            item = dict(entry)
            item.setdefault("short", default_short(str(item["name"])))
            item.setdefault("kind", "RESEARCH")
            item.setdefault("cats", ["research"])
            item.setdefault("killer", item.get("summary", "GitHubで公開中です。"))
            item.setdefault("desc", item.get("summary", ""))
            item.setdefault("definition", item.get("summary", ""))
            item.setdefault("url", f"https://github.com/nobutakayamauchi/{Path(root).name}")
            item.setdefault("priority", 500)
            item["source"] = f"repo:{Path(root).name}"
            found.append(item)
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True)
    parser.add_argument("--sales-products")
    parser.add_argument("--repo", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    seed = read_json(Path(args.seed), {"editorial": {}, "static_items": []})
    editorial = seed.get("editorial", {})
    items_by_id = {}

    for item in seed.get("static_items", []):
        if isinstance(item, dict) and item.get("id") and item.get("status", "public") != "hidden":
            enriched = dict(item)
            enriched.setdefault("source", "seed")
            items_by_id[enriched["id"]] = enriched

    if args.sales_products:
        for product in read_json(Path(args.sales_products), []):
            if not isinstance(product, dict) or product.get("status") != "for_sale" or not product.get("id"):
                continue
            items_by_id[product["id"]] = sales_item(product, editorial)

    for item in manifest_items(args.repo):
        current = items_by_id.get(item["id"])
        if current and current.get("source") == "sales-catalog":
            continue
        merged = dict(current or {})
        merged.update(item)
        if item["id"] in editorial:
            merged.update(editorial[item["id"]])
        items_by_id[item["id"]] = merged

    items = sorted(items_by_id.values(), key=lambda x: (int(x.get("priority", 999)), str(x.get("name", ""))))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"catalog: {len(items)} public items -> {out}")


if __name__ == "__main__":
    main()
