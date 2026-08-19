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
        assert text in index or text in (ROOT / "assets/home.js").read_text(encoding="utf-8"), f"missing adopted copy: {text}"

    css = (ROOT / "assets/home.css").read_text(encoding="utf-8")
    for bp in ("max-width:820px", "max-width:520px", "max-width:390px"):
        assert bp in css, f"missing responsive breakpoint: {bp}"
    assert "width:100%" in css, "homepage should include fluid-width rules"

    html_files = [ROOT / "index.html", ROOT / "foundry-spec.html", *sorted((ROOT / "products").glob("*.html"))]
    for html in html_files:
        parser = LinkParser()
        parser.feed(html.read_text(encoding="utf-8"))
        assert_local_links(html)

    print(f"homepage checks passed: {len(html_files)} html files")

if __name__ == "__main__":
    main()
