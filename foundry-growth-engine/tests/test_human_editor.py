from __future__ import annotations

from pathlib import Path
import unittest

from fge.core import Evidence, Update, build_update, build_journals, load_knowledge
from fge.human_editor import HumanEditorV0, humanize_updates, humanize_journals

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
KNOWLEDGE = load_knowledge(str(ROOT / 'config/knowledge.limit-development.json'))
PLAIN = load_knowledge(str(ROOT / 'config/knowledge.plain.json'))


class HumanEditorTest(unittest.TestCase):
    def ev(self, sid='e1', text='Fix journal navigation', captured='2026-08-20T18:00:00+09:00'):
        return Evidence(
            source_id=sid,
            captured_at=captured,
            actor='tester',
            text=text,
            source_type='test',
            project_hint='FOUNDRY GROWTH ENGINE',
            raw_evidence_ref=f'commit:{sid}',
        )

    def test_human_editor_preserves_trace_identity(self):
        ev = self.ev()
        original = build_update(ev, KNOWLEDGE)
        edited = HumanEditorV0(KNOWLEDGE).edit_update(original, ev.text)
        self.assertEqual(original.id, edited.id)
        self.assertEqual(original.source_id, edited.source_id)
        self.assertEqual(original.raw_evidence_ref, edited.raw_evidence_ref)
        self.assertEqual(original.type, edited.type)
        self.assertEqual(original.project, edited.project)

    def test_human_editor_does_not_invent_numbers(self):
        ev = self.ev(text='Improve journal navigation')
        original = build_update(ev, KNOWLEDGE)
        edited = HumanEditorV0(KNOWLEDGE).edit_update(original, ev.text)
        self.assertNotRegex(edited.summary, r'\d+[%件倍人円]')

    def test_human_preserves_learned_and_hourly_context(self):
        original = Update(
            id='u', source_id='s', captured_at='2026-08-20T18:00:00+09:00',
            type='機能変更', project='FOUNDRY GROWTH ENGINE',
            title='FOUNDRY GROWTH ENGINEを改善',
            summary='FOUNDRY GROWTH ENGINEを改善しました。リンクが動くことより、読者が実際に目的の中身まで着けることを重視しています。 同じ1時間内の関連変更3件も、この更新にまとめています。',
            raw_evidence_ref='commit:s'
        )
        edited = HumanEditorV0(KNOWLEDGE).edit_update(original)
        self.assertIn('読者が実際に目的の中身まで着ける', edited.summary)
        self.assertIn('関連変更3件', edited.summary)

    def test_humanized_update_flows_into_single_item_journal(self):
        ev = self.ev()
        original = build_update(ev, KNOWLEDGE)
        edited = humanize_updates([original], {ev.source_id: ev}, KNOWLEDGE)[0]
        journal = build_journals([edited])[0]
        journal = humanize_journals([journal], [edited], KNOWLEDGE)[0]
        self.assertEqual(journal.title, edited.title)
        self.assertEqual(journal.summary, edited.summary)

    def test_multi_item_journal_gets_readable_lead_without_losing_ids(self):
        aev = self.ev('a', 'Fix journal navigation', '2026-08-20T18:00:00+09:00')
        bev = self.ev('b', 'Improve publishing flow', '2026-08-20T19:00:00+09:00')
        updates = [build_update(aev, KNOWLEDGE), build_update(bev, KNOWLEDGE)]
        edited = humanize_updates(updates, {'a': aev, 'b': bev}, KNOWLEDGE)
        original_journal = build_journals(edited)[0]
        human_journal = humanize_journals([original_journal], edited, KNOWLEDGE)[0]
        self.assertEqual(human_journal.update_ids, original_journal.update_ids)
        self.assertIn('ほか1件', human_journal.title)
        self.assertIn('同じ日の開発記録として', human_journal.summary)

    def test_plain_output_is_unchanged_without_human(self):
        ev = self.ev(text='Fix retry queue ordering')
        a = build_update(ev, PLAIN)
        b = build_update(ev, PLAIN)
        self.assertEqual(a.title, b.title)
        self.assertEqual(a.summary, b.summary)

    def test_editor_only_uses_public_profile_context(self):
        ev = self.ev(text='Improve publishing flow')
        original = build_update(ev, KNOWLEDGE)
        edited = HumanEditorV0(KNOWLEDGE).edit_update(original, ev.text)
        forbidden = KNOWLEDGE.get('safety', {}).get('never_infer', [])
        for phrase in forbidden:
            self.assertNotIn(str(phrase), edited.summary)


if __name__ == '__main__':
    unittest.main()
