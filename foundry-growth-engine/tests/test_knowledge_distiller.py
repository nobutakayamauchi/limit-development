from __future__ import annotations

import json
from pathlib import Path
import unittest

from fge.core import Evidence, build_update, load_knowledge
from fge.knowledge_distiller import distill, load_jsonl, load_rules

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
BASE = load_knowledge(str(ROOT / 'config/knowledge.limit-development.json'))
PLAIN = load_knowledge(str(ROOT / 'config/knowledge.plain.json'))
RULES = load_rules(ROOT / 'config/distiller.rules.json')
SAMPLE = ROOT / 'tests/fixtures/chat-sample.safe.jsonl'


class KnowledgeDistillerTest(unittest.TestCase):
    def ev(self, text='Improve knowledge writer mode'):
        return Evidence(
            source_id='same-evidence',
            captured_at='2026-08-20T02:00:00+09:00',
            actor='tester',
            text=text,
            source_type='test',
            project_hint='FOUNDRY GROWTH ENGINE',
            raw_evidence_ref='commit:same-evidence',
        )

    def test_safe_sample_promotes_repeated_observations(self):
        learned, report = distill(load_jsonl(SAMPLE), BASE, RULES)
        self.assertEqual(report['unique_input_count'], 6)
        self.assertEqual(report['promoted_rule_count'], 3)
        self.assertEqual(len(learned['learned_context_rules']), 3)

    def test_single_utterance_does_not_become_trait(self):
        one = [{
            'source_id': 'one',
            'text': 'あー、もう面倒くてえな',
            'project': 'FOUNDRY GROWTH ENGINE',
            'allow_public_learning': True,
        }]
        learned, report = distill(one, BASE, RULES)
        ids = {x['id'] for x in learned['learned_context_rules']}
        self.assertNotIn('friction_to_automation', ids)
        self.assertEqual(report['promoted_rule_count'], 0)

    def test_duplicate_source_and_non_allowlisted_chat_do_not_count(self):
        items = [
            {'source_id': 'a', 'text': 'ナレッジなしで出す', 'allow_public_learning': True},
            {'source_id': 'a', 'text': 'プレーンをキープ', 'allow_public_learning': True},
            {'source_id': 'b', 'text': 'プレーンをキープ', 'allow_public_learning': False},
        ]
        learned, _ = distill(items, BASE, RULES)
        ids = {x['id'] for x in learned['learned_context_rules']}
        self.assertNotIn('replaceable_personalization', ids)

    def test_derived_pack_never_persists_raw_chat_text(self):
        entries = load_jsonl(SAMPLE)
        learned, _ = distill(entries, BASE, RULES)
        serialized = json.dumps(learned, ensure_ascii=False)
        for item in entries:
            self.assertNotIn(item['text'], serialized)
        self.assertFalse(learned['distillation']['raw_chat_persisted'])

    def test_same_evidence_has_plain_current_and_chat_learned_modes(self):
        learned, _ = distill(load_jsonl(SAMPLE), BASE, RULES)
        ev = self.ev()
        plain = build_update(ev, PLAIN)
        current = build_update(ev, BASE)
        chat = build_update(ev, learned)
        self.assertEqual(plain.source_id, current.source_id)
        self.assertEqual(current.source_id, chat.source_id)
        self.assertNotEqual(plain.summary, current.summary)
        self.assertNotEqual(current.summary, chat.summary)
        self.assertIn('プレーン版へ戻れる', chat.summary)


if __name__ == '__main__':
    unittest.main()
