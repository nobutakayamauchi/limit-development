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
    def test_busy_day_is_grouped_into_project_chapters(self):
        items = [
            update(1, '09', '導線を修正', '一覧ではなく本文へ直接着けるようにしました。'),
            update(2, '12', '開発記録を自動化', '公開Gitの活動から開発記録を更新するようにしました。'),
            update(3, '18', 'ナレッジを追加', '意味を補うKnowledge層を追加しました。', kind='機能追加'),
            update(4, '19', 'Bridge接続を修正', '接続まわりを修正しました。', project='WebAI Bridge'),
            update(5, '20', 'Loopを検証', '開発ループを検証しました。', project='Ultimate Loop', kind='研究・検証'),
        ]
        j = Journal('2026-08-20', '5件の更新', '短いリード', [x.id for x in items], ['FOUNDRY GROWTH ENGINE','WebAI Bridge','Ultimate Loop'], ['機能変更','機能追加','研究・検証'], [])
        knowledge = {'project_profiles': {'FOUNDRY GROWTH ENGINE': {'public_description': '仕事の記録から公開直前まで整える仕組みです。'}}}
        body = generate_journal_body(j, items, knowledge=knowledge)
        self.assertIn('## 今日の中心', body)
        self.assertIn('## まとまりごとの記録', body)
        self.assertIn('### FOUNDRY GROWTH ENGINE — 3件', body)
        self.assertIn('### WebAI Bridge — 1件', body)
        self.assertIn('### Ultimate Loop — 1件', body)
        self.assertIn('最も多かったのはFOUNDRY GROWTH ENGINEの3件', body)
        self.assertIn('仕事の記録から公開直前まで整える仕組みです。', body)
        self.assertIn('## 今日の結論', body)
        self.assertIn('FOUNDRY GROWTH ENGINEの3件を中心に', body)
        self.assertGreater(len(body), len(j.summary) * 8)

    def test_large_single_project_uses_checkpoints_not_full_log(self):
        items = [update(i, f'{8+i:02d}', f'変更{i}', f'変更{i}を反映しました。') for i in range(1, 8)]
        j = Journal('2026-08-20', '7件', 'lead', [x.id for x in items], [items[0].project], [items[0].type], [])
        body = generate_journal_body(j, items)
        self.assertIn('### FOUNDRY GROWTH ENGINE — 7件', body)
        self.assertIn('ほか4件の更新', body)
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
            count = expand_rendered_journals(root, [j], [item], knowledge={})
            text = page.read_text(encoding='utf-8')
            self.assertEqual(count, 1)
            self.assertIn('journal-generated', text)
            self.assertIn('今日の中心', text)
            self.assertIn('<article>existing</article>', text)

    def test_missing_page_is_safe(self):
        j = Journal('2026-08-20', '日誌', 'lead', [], [], [], [])
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(expand_rendered_journals(td, [j], [], knowledge={}), 0)


if __name__ == '__main__':
    unittest.main()
