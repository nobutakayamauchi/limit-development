import tempfile, unittest
from pathlib import Path
from fge.core import Evidence, build_update, build_article, build_journals
from fge.adapters.pages_output import render_site

class ReviewBoundaryTest(unittest.TestCase):
    def test_review_chrome_is_not_in_public_article(self):
        ev = Evidence('a','2026-08-19T12:00:00+09:00','x','launch product',project_hint='TEST',explicit_intent='FORCE_ARTICLE')
        u = build_update(ev,{})
        a = build_article(u,ev,{})
        with tempfile.TemporaryDirectory() as td:
            render_site(td,[u],[a],build_journals([u]),'2026-08-19T12:00+09:00')
            public = Path(td,f'articles/{a.id}.html').read_text(encoding='utf-8')
            review = Path(td,'review/index.html').read_text(encoding='utf-8')
            self.assertNotIn('REVIEW REQUIRED', public)
            self.assertNotIn('レビューこれです。投稿しますか？', public)
            self.assertIn('レビューこれです。投稿しますか？', review)

if __name__ == '__main__': unittest.main()
