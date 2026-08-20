from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from fge.core import Journal, Update
from fge.journal_generator import generate_journal_body, journal_body_html, expand_rendered_journals


def update(i, hour, title, summary, project='FOUNDRY GROWTH ENGINE', kind='機能変更'):
    return Update(
        id=f'u{i}', source_id=f's{i}', captured_at=f'2026-08-20T{hour}:00:00+09:00',
        type=kind, project=project, title=title, summary=summary,
        tags=[project, kind], raw_evidence_ref=f'commit:{i}'
    )


class JournalGeneratorTest(unittest.TestCase):
    def test_busy_day_separates_daily_intent_git_facts_and_stable_goal(self):
        items = [
            update(1, '09', '導線を修正', '一覧ではなく本文へ直接着けるようにしました。'),
            update(2, '12', '開発記録を自動化', '公開Gitの活動から開発記録を更新するようにしました。'),
            update(3, '18', 'ナレッジを追加', '意味を補うKnowledge層を追加しました。', kind='機能追加'),
            update(4, '19', 'Bridge接続を修正', '接続まわりを修正しました。', project='WebAI Bridge'),
        ]
        j = Journal('2026-08-20', '4件の更新', '短いリード', [x.id for x in items], ['FOUNDRY GROWTH ENGINE','WebAI Bridge'], ['機能変更','機能追加'], [])
        knowledge = {'project_profiles': {
            'FOUNDRY GROWTH ENGINE': {
                'public_description': '仕事の記録から公開直前まで整える仕組みです。',
                'why_it_matters': '投稿を考える別の仕事を増やさないために使います。',
            },
            'WebAI Bridge': {'why_it_matters': '使うAIが変わっても利用場所まで捨てないためです。'},
        }}
        intents = [{
            'observation_id':'g1','date':'2026-08-20','project':'FOUNDRY GROWTH ENGINE',
            'intent':'何を狙って何をやり、どこまで進んだかが分かる日誌にする。',
            'source_type':'goal','approval_status':'approved','public_safe':True,'allow_journal':True,
        }]
        body = generate_journal_body(j, items, knowledge=knowledge, daily_intents=intents)
        self.assertIn('## 今日の狙い', body)
        self.assertIn('何を狙って何をやり、どこまで進んだかが分かる日誌にする。', body)
        self.assertIn('/goalとして公開利用を承認した記録', body)
        self.assertIn('## この開発の目的', body)
        self.assertIn('投稿を考える別の仕事を増やさないために使います。', body)
        self.assertIn('## 今日やったこと', body)
        self.assertIn('### FOUNDRY GROWTH ENGINE — 3件', body)
        self.assertIn('実際の変更内訳:', body)
        self.assertIn('## 今日どこまで進んだか', body)
        self.assertIn('公開Git上でいちばん新しい到達点は「ナレッジを追加」', body)
        self.assertIn('狙いを完全に達成したという判定はしていません', body)

    def test_daily_goal_is_not_inferred_from_git_or_stable_knowledge(self):
        item = update(1, '09', '導線を修正', '本文へ直接着けるようにしました。')
        j = Journal('2026-08-20', '1件', 'lead', [item.id], [item.project], [item.type], [])
        knowledge = {'project_profiles': {item.project: {'why_it_matters': '投稿作業を減らすためです。'}}}
        body = generate_journal_body(j, [item], knowledge=knowledge, daily_intents=[])
        self.assertNotIn('## 今日の狙い', body)
        self.assertIn('## この開発の目的', body)
        self.assertIn('投稿作業を減らすためです。', body)

    def test_repo_shaped_project_name_resolves_identity_safe_goal_and_daily_intent_alias(self):
        item = update(1, '09', 'Bridge接続を修正', '接続まわりを修正しました。', project='WebAI-Bridge')
        j = Journal('2026-08-20', '1件', 'lead', [item.id], [item.project], [item.type], [])
        knowledge = {
            'project_aliases': [{'pattern': 'webai bridge|web ai bridge', 'project': 'WebAI Bridge'}],
            'project_profiles': {'WebAI Bridge': {'why_it_matters': '利用場所まで捨てないためです。'}},
        }
        intents = [{'observation_id':'c1','date':'2026-08-20','project':'WebAI Bridge','intent':'接続を安定させる。','source_type':'chat_observation','approval_status':'approved','public_safe':True,'allow_journal':True}]
        body = generate_journal_body(j, [item], knowledge=knowledge, daily_intents=intents)
        self.assertIn('## 今日の狙い', body)
        self.assertIn('接続を安定させる。', body)
        self.assertIn('承認済みChat Observation', body)
        self.assertIn('利用場所まで捨てないためです。', body)

    def test_broad_semantic_alias_does_not_attach_wrong_product_purpose(self):
        item = update(1, '09', 'サイトを更新', '公開ページを更新しました。', project='limit-development')
        j = Journal('2026-08-20', '1件', 'lead', [item.id], [item.project], [item.type], [])
        knowledge = {
            'project_aliases': [{'pattern': 'one phone foundry|homepage|mobile layout|limit-development', 'project': 'ONE PHONE FOUNDRY'}],
            'project_profiles': {'ONE PHONE FOUNDRY': {'public_description':'スマホを司令塔にする環境です。','why_it_matters':'スマホから指示を飛ばすためです。'}},
        }
        intents = [{'observation_id':'x','date':'2026-08-20','project':'ONE PHONE FOUNDRY','intent':'スマホ画面を磨く。','source_type':'goal'}]
        body = generate_journal_body(j, [item], knowledge=knowledge, daily_intents=intents)
        self.assertNotIn('スマホを司令塔にする環境です。', body)
        self.assertNotIn('スマホから指示を飛ばすためです。', body)
        self.assertNotIn('スマホ画面を磨く。', body)

    def test_large_single_project_uses_checkpoints_not_full_log(self):
        items = [update(i, f'{8+i:02d}', f'変更{i}', f'変更{i}を反映しました。') for i in range(1, 8)]
        j = Journal('2026-08-20', '7件', 'lead', [x.id for x in items], [items[0].project], [items[0].type], [])
        body = generate_journal_body(j, items)
        self.assertIn('### FOUNDRY GROWTH ENGINE — 7件', body)
        self.assertIn('ほか4件の公開Git由来の更新', body)
        self.assertLess(body.count(' — 変更'), 7)

    def test_html_escapes_content_and_supports_cluster_heading(self):
        html = journal_body_html('## 今日の中心\n### <script>project</script>\n<script>alert(1)</script>\n- <b>項目</b>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;project&lt;/script&gt;', html)
        self.assertIn('journal-cluster', html)
        self.assertIn('&lt;b&gt;項目&lt;/b&gt;', html)

    def test_expansion_replaces_only_exact_lead(self):
        item = update(1, '09', '導線を修正', '本文へ直接着けるようにしました。')
        j = Journal('2026-08-20', '日誌', '短いリード', [item.id], [item.project], [item.type], [])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            page = root / 'journal' / '2026-08-20.html'
            page.parent.mkdir(parents=True)
            page.write_text('<html><p>短いリード</p><article>existing</article></html>', encoding='utf-8')
            count = expand_rendered_journals(root, [j], [item], knowledge={}, daily_intents=[])
            text = page.read_text(encoding='utf-8')
            self.assertEqual(count, 1)
            self.assertIn('journal-generated', text)
            self.assertIn('今日の中心', text)
            self.assertIn('<article>existing</article>', text)

    def test_missing_page_is_safe(self):
        j = Journal('2026-08-20', '日誌', 'lead', [], [], [], [])
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(expand_rendered_journals(td, [j], [], knowledge={}, daily_intents=[]), 0)


if __name__ == '__main__':
    unittest.main()
