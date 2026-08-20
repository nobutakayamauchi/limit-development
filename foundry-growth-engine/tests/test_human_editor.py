from __future__ import annotations

from pathlib import Path
import unittest

from fge.core import Evidence, build_update, build_journals, load_knowledge
from fge.human_editor import HumanEditorV0, humanize_updates

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
KNOWLEDGE = load_knowledge(str(ROOT / 'config/knowledge.limit-development.json'))
PLAIN = load_knowledge(str(ROOT / 'config/knowledge.plain.json'))


class HumanEditorTest(unittest.TestCase):
    def ev(self, sid='e1', text='Fix journal navigation'):
        return Evidence(
            source_id=sid,
            captured_at='2026-08-20T18:00:00+09:00',
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

    def test_humanized_update_flows_into_journal(self):
        ev = self.ev()
        original = build_update(ev, KNOWLEDGE)
        edited = humanize_updates([original], {ev.source_id: ev}, KNOWLEDGE)[0]
        journal = build_journals([edited])[0]
        self.assertEqual(journal.title, edited.title)
        self.assertIn(edited.title, journal.summary)

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
