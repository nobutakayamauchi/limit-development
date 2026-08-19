from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from fge.core import Evidence, INTENT_FORCE_ARTICLE, INTENT_RECORD_ONLY, build_update, build_article, build_journals, load_knowledge
from fge.adapters.pages_output import render_site

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
KNOWLEDGE = load_knowledge(str(ROOT/'config/knowledge.limit-development.json'))

class FGETest(unittest.TestCase):
    def ev(self, sid='abc', text='fix parser', captured='2026-08-19T10:00:00+09:00', intent='AUTO'):
        return Evidence(source_id=sid, captured_at=captured, actor='tester', text=text, source_type='test', explicit_intent=intent, raw_evidence_ref=f'commit:{sid}')

    def test_known_commit_becomes_human_update(self):
        u = build_update(self.ev(text='Revert broken mobile layout'), KNOWLEDGE)
        self.assertEqual(u.type, '機能変更')
        self.assertEqual(u.title, 'スマホ表示を安定版へ復元')

    def test_fge_self_birth_is_article_candidate(self):
        u = build_update(self.ev(text='Scaffold Foundry Growth Engine core architecture'), KNOWLEDGE)
        self.assertEqual(u.type, '新製品')
        self.assertTrue(u.article_candidate)
        self.assertGreater(u.article_score, .9)

    def test_record_only_overrides_everything(self):
        u = build_update(self.ev(text='Launch revolutionary product', intent=INTENT_RECORD_ONLY), KNOWLEDGE)
        self.assertFalse(u.article_candidate)
        self.assertEqual(u.article_score, 0)

    def test_force_article_overrides_short_input(self):
        u = build_update(self.ev(text='tiny', intent=INTENT_FORCE_ARTICLE), {})
        self.assertTrue(u.article_candidate)
        self.assertEqual(u.article_score, 1)

    def test_journal_groups_without_destroying_updates(self):
        a = build_update(self.ev('a','add feature','2026-08-19T09:00:00+09:00'), {})
        b = build_update(self.ev('b','fix bug','2026-08-19T10:00:00+09:00'), {})
        js = build_journals([a,b])
        self.assertEqual(len(js), 1)
        self.assertEqual(set(js[0].update_ids), {a.id,b.id})

    def test_plain_core_has_no_operator_voice(self):
        plain = load_knowledge(str(ROOT/'config/knowledge.plain.json'))
        u = build_update(self.ev(text='Scaffold Foundry Growth Engine core architecture'), plain)
        self.assertNotEqual(u.title, 'FOUNDRY GROWTH ENGINEを開発')

    def test_static_site_latest_five_and_search_index(self):
        updates = [build_update(self.ev(str(i),f'add feature {i}',f'2026-08-{19-i:02d}T10:00:00+09:00'), {}) for i in range(7)]
        articles = [build_article(updates[0], self.ev('0','add feature 0'), {})]
        journals = build_journals(updates)
        with tempfile.TemporaryDirectory() as td:
            render_site(td, updates, articles, journals, '2026-08-19T11:00+09:00')
            html = Path(td,'updates/index.html').read_text(encoding='utf-8')
            self.assertEqual(html.count('class="journal"'), 5)
            self.assertTrue(Path(td,'archive/index.html').exists())
            idx = json.loads(Path(td,'data/search-index.json').read_text(encoding='utf-8'))
            self.assertTrue(any(x['kind']=='JOURNAL' for x in idx))
            self.assertTrue(any(x['kind']=='ARTICLE' for x in idx))

    def test_no_change_rebuild_only_changes_status_time(self):
        u = build_update(self.ev('same','fix bug'), {})
        with tempfile.TemporaryDirectory() as td:
            render_site(td,[u],[],build_journals([u]),'2026-08-19T11:00+09:00')
            before = Path(td,'data/updates.json').read_text(encoding='utf-8')
            render_site(td,[u],[],build_journals([u]),'2026-08-19T12:00+09:00')
            after = Path(td,'data/updates.json').read_text(encoding='utf-8')
            status = json.loads(Path(td,'data/status.json').read_text(encoding='utf-8'))
            self.assertEqual(before, after)
            self.assertEqual(status['checked_at'], '2026-08-19T12:00+09:00')

    def test_writer_engine_is_separate_module(self):
        from fge.engines import RuleBasedPublicWriter
        self.assertEqual(RuleBasedPublicWriter.name, 'rule-based-v0')

    def test_mobile_breakpoint_guards_present(self):
        src = (ROOT/'fge/adapters/pages_output.py').read_text(encoding='utf-8')
        self.assertIn('@media(max-width:375px)', src)
        self.assertIn('@media(max-width:390px)', src)
        self.assertIn('@media(max-width:430px)', src)

if __name__ == '__main__': unittest.main()
