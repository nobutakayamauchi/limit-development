from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "index.html",
    "assets/home.css",
    "assets/home.js",
    "assets/product.css",
    "33D84490-07CF-4D02-8492-7CB91EC9B585.png",
    "foundry-spec.html",
    "works/index.html",
    "products/foundry-growth-engine.html",
    "products/ultimate-loop.html",
    "products/webai-bridge.html",
    "products/bridgepatch.html",
    "products/axis.html",
    "products/nagi.html",
    "products/trace.html",
]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        for key in ("href", "src"):
            if key in data:
                self.refs.append((key, data[key]))


def assert_local_links(html_path: Path) -> None:
    parser = LinkParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    for _, ref in parser.refs:
        if not ref or ref.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        parsed = urlparse(ref)
        if parsed.scheme in {"http", "https"} or ref.startswith("//"):
            continue
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        target = (html_path.parent / clean).resolve()
        if target.is_dir():
            target = target / "index.html"
        assert target.exists(), f"broken local ref in {html_path.relative_to(ROOT)}: {ref}"


def main() -> None:
    for rel in REQUIRED:
        path = ROOT / rel
        assert path.exists(), f"missing required homepage asset: {rel}"

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "assets/home.js").read_text(encoding="utf-8")
    for text in [
        "仕事してください。",
        "一からの新造、やめてください。",
        "ここ直せば、大体直ります。",
        "たくさんあっても、今やるのはこれだけです。",
        "中断した場所？ここからです。",
        "「何が起きた？」慌てずこれ見てください。",
        "YouTube",
        "LINE",
        "メルマガ",
        "COMING SOON",
        "こんな状況でも、スマホ1台でここまで作れます。",
    ]:
        assert text in index or text in js, f"missing adopted copy: {text}"

    # FGE live boards are progressive enhancement: static fallback must remain usable
    # before the first reviewed publish creates /data, /updates, /journal and /archive.
    for marker in ('id="updateFeed"', 'id="journalFeed"', 'id="updateAllLink"', 'id="journalIndexLink"'):
        assert marker in index, f"missing FGE homepage hook: {marker}"
    assert 'href="status.html"' in index, "UPDATE fallback link must remain valid before FGE publish"
    assert 'href="development.html">INDEX' in index, "JOURNAL fallback link must remain valid before FGE publish"
    for literal in (
        "data/updates.json",
        "data/journals.json",
        "Array.isArray(updates)&&updates.length",
        "Array.isArray(journals)&&journals.length",
        "updateFeed.replaceChildren",
        "journalFeed.replaceChildren",
        "catch(_){/* reviewed FGE bundle not published yet: keep static fallback */}",
        "catch(_){/* keep static fallback */}",
    ):
        assert literal in js, f"missing safe FGE live-feed behavior: {literal}"
    assert "a.textContent=String(u.title" in js, "FGE update title must be inserted with textContent"
    assert "a.textContent=String(j.title" in js, "FGE journal title must be inserted with textContent"

    # The rail's ALL INDEX is a real shelf, not a fake reset button.
    assert "window.location.href='works/'" in js, "ALL INDEX must open works/"
    works = (ROOT / "works/index.html").read_text(encoding="utf-8")
    for name in ("FOUNDRY GROWTH ENGINE", "Ultimate Loop", "WebAI Bridge", "BridgePatch", "AXIS", "NAGI", "TRACE"):
        assert name in works, f"works index missing: {name}"

    css = (ROOT / "assets/home.css").read_text(encoding="utf-8")
    for bp in ("max-width:820px", "max-width:520px", "max-width:390px"):
        assert bp in css, f"missing responsive breakpoint: {bp}"
    assert "width:100%" in css, "homepage should include fluid-width rules"

    html_files = [ROOT / "index.html", ROOT / "foundry-spec.html", ROOT / "works/index.html", *sorted((ROOT / "products").glob("*.html"))]
    for html in html_files:
        assert_local_links(html)

    print(f"homepage checks passed: {len(html_files)} html files; FGE live hooks + works index verified")

if __name__ == "__main__":
    main()
