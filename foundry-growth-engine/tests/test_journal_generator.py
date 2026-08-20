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
    def test_multi_update_day_has_real_sections_and_flow(self):
        items = [
            update(1, '09', '導線を修正', '一覧ではなく本文へ直接着けるようにしました。'),
            update(2, '12', '開発記録を自動化', '公開Gitの活動から開発記録を更新するようにしました。'),
            update(3, '18', 'ナレッジを追加', '意味を補うKnowledge層を追加しました。', kind='機能追加'),
        ]
        j = Journal('2026-08-20', '3件の更新', '短いリード', [x.id for x in items], ['FOUNDRY GROWTH ENGINE'], ['機能変更','機能追加'], [])
        body = generate_journal_body(j, items)
        self.assertIn('## 今日やったこと', body)
        self.assertIn('## 開発の流れ', body)
        self.assertIn('合計3件', body)
        self.assertIn('09:00 導線を修正', body)
        self.assertIn('## 今日の結論', body)
        self.assertGreater(len(body), len(j.summary) * 4)

    def test_html_escapes_content(self):
        html = journal_body_html('## 今日やったこと\n<script>alert(1)</script>\n- <b>項目</b>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;b&gt;項目&lt;/b&gt;', html)

    def test_expansion_replaces_only_exact_lead(self):
        item = update(1, '09', '導線を修正', '本文へ直接着けるようにしました。')
        j = Journal('2026-08-20', '日誌', '短いリード', [item.id], [item.project], [item.type], [])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            page = root / 'journal' / '2026-08-20.html'
            page.parent.mkdir(parents=True)
            page.write_text('<html><p>短いリード</p><article>existing</article></html>', encoding='utf-8')
            count = expand_rendered_journals(root, [j], [item])
            text = page.read_text(encoding='utf-8')
            self.assertEqual(count, 1)
            self.assertIn('journal-generated', text)
            self.assertIn('今日やったこと', text)
            self.assertIn('<article>existing</article>', text)

    def test_missing_page_is_safe(self):
        j = Journal('2026-08-20', '日誌', 'lead', [], [], [], [])
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(expand_rendered_journals(td, [j], []), 0)


if __name__ == '__main__':
    unittest.main()
