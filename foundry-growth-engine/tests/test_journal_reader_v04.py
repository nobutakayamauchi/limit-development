from __future__ import annotations

import unittest

from fge.core import Journal, Update
from fge.human_editor import humanize_journals
from fge.journal_reader_v04 import generate_reader_body


def update(i, hour, title, summary, project='FOUNDRY GROWTH ENGINE', kind='機能追加'):
    return Update(
        id=f'u{i}', source_id=f's{i}', captured_at=f'2026-08-20T{hour}:00:00+09:00',
        type=kind, project=project, title=title, summary=summary,
        tags=[project, kind], raw_evidence_ref=f'commit:{i}'
    )


class JournalReaderV04Test(unittest.TestCase):
    def setUp(self):
        self.knowledge = {
            'project_profiles': {
                'FOUNDRY GROWTH ENGINE': {
                    'public_description': '仕事の記録から公開前レビューまで整える投稿支援ツールです。',
                    'why_it_matters': '仕事のあとに投稿を考える別の仕事を増やさないための仕組みです。',
                },
                'WebAI Bridge': {
                    'public_description': 'AI機能を自分の場所へつなぐ接続基盤です。',
                    'why_it_matters': '使うAIが変わっても利用場所まで捨てなくて済む形を目指します。',
                },
            }
        }
        self.intent = [{
            'observation_id': 'goal1', 'date': '2026-08-20',
            'project': 'FOUNDRY GROWTH ENGINE',
            'intent': '開発日誌を、何を狙って何をやり、今日どこまで進んだかが読めば分かる開発記録にする。',
            'source_type': 'goal', 'approval_status': 'approved',
            'public_safe': True, 'allow_journal': True, 'source_ref': 'goal:test'
        }]

    def test_title_uses_daily_meaning_and_counts_leave_headline(self):
        items = [
            update(1, '09', 'FGEに機能を追加', 'FGEに機能を追加しました。仕事のあとに投稿を考える作業を減らすための変更です。'),
            update(2, '12', '日誌を改善', '日誌を改善しました。狙いと実作業を分けて読めるようにしました。', kind='機能変更'),
        ]
        j = Journal('2026-08-20', '2件', 'lead', [x.id for x in items], [items[0].project], ['機能追加','機能変更'], [])
        edited = humanize_journals([j], items, self.knowledge, daily_intents=self.intent)[0]
        self.assertIn('開発日誌を', edited.title)
        self.assertIn('にした日', edited.title)
        self.assertNotIn('ほか1件', edited.title)
        self.assertIn('2件', edited.summary)

    def test_public_body_hides_internal_audit_explanations(self):
        item = update(1, '09', '日誌を改善', '日誌を改善しました。狙いと実作業を分けて読めるようにしました。', kind='機能変更')
        j = Journal('2026-08-20', '1件', 'lead', [item.id], [item.project], [item.type], [])
        body = generate_reader_body(j, [item], self.knowledge, self.intent)
        self.assertIn('## 今日の狙い', body)
        self.assertIn('## この開発の目的', body)
        self.assertNotIn('公開利用を承認した記録', body)
        self.assertNotIn('その日の推測ではなく', body)
        self.assertNotIn('完全に達成したという判定', body)

    def test_change_line_prefers_what_improved_over_repeating_git_title(self):
        item = update(1, '09', 'FGEに機能を追加', 'FGEに機能を追加しました。疲れた後に投稿文を考える作業を減らせるようにしました。')
        j = Journal('2026-08-20', '1件', 'lead', [item.id], [item.project], [item.type], [])
        body = generate_reader_body(j, [item], self.knowledge, self.intent)
        self.assertIn('疲れた後に投稿文を考える作業を減らせるようにしました。', body)
        bullet = next(line for line in body.splitlines() if line.startswith('- '))
        self.assertNotIn('FGEに機能を追加しました。', bullet)

    def test_project_counts_are_supporting_metadata(self):
        items = [
            update(1, '09', '変更A', '変更Aを反映しました。'),
            update(2, '10', '変更B', '変更Bを反映しました。'),
            update(3, '11', 'Bridge改善', '接続先の説明を分かりやすくしました。', project='WebAI Bridge', kind='機能変更'),
        ]
        j = Journal('2026-08-20', '3件', 'lead', [x.id for x in items], ['FOUNDRY GROWTH ENGINE','WebAI Bridge'], ['機能追加','機能変更'], [])
        body = generate_reader_body(j, items, self.knowledge, self.intent)
        self.assertIn('### FOUNDRY GROWTH ENGINE', body)
        self.assertNotIn('### FOUNDRY GROWTH ENGINE — 2件', body)
        self.assertIn('記録: 2件', body)


if __name__ == '__main__':
    unittest.main()
