from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from fge.core import Evidence, build_update, load_knowledge
from fge.knowledge_distiller import distill, load_jsonl, load_rules
from fge.preference_loop import (
    STAGE_ACTIVE,
    STAGE_DORMANT,
    STAGE_SHADOW,
    apply_preference_feedback,
    load_feedback,
)

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
BASE = load_knowledge(str(ROOT / 'config/knowledge.limit-development.json'))
RULES = load_rules(ROOT / 'config/distiller.rules.json')
CHAT = ROOT / 'tests/fixtures/chat-sample.safe.jsonl'
FEEDBACK = ROOT / 'tests/fixtures/preference-feedback.safe.jsonl'


def learned_pack():
    return distill(load_jsonl(CHAT), BASE, RULES)[0]


class PreferenceLoopTest(unittest.TestCase):
    def test_dogfood_has_active_shadow_and_dormant(self):
        derived, report = apply_preference_feedback(learned_pack(), load_feedback(FEEDBACK))
        states = {x['id']: x['preference']['stage'] for x in derived['learned_context_rules']}
        self.assertEqual(states['friction_to_automation'], STAGE_ACTIVE)
        self.assertEqual(states['destination_over_link_success'], STAGE_SHADOW)
        self.assertEqual(states['replaceable_personalization'], STAGE_DORMANT)
        self.assertEqual(report['stage_counts'], {'SHADOW': 1, 'ACTIVE': 1, 'DORMANT': 1})

    def test_no_feedback_stays_shadow(self):
        derived, _ = apply_preference_feedback(learned_pack(), [])
        self.assertTrue(all(x['preference']['stage'] == STAGE_SHADOW for x in derived['learned_context_rules']))

    def test_duplicate_feedback_id_counts_once(self):
        row = {
            'feedback_id': 'dup', 'rule_id': 'friction_to_automation', 'surface': 'journal',
            'ratings': {'voice_fit': 2, 'readability': 2, 'factual_fidelity': 2, 'task_fit': 2},
            'allow_preference_learning': True,
        }
        derived, report = apply_preference_feedback(learned_pack(), [row, dict(row)])
        rule = next(x for x in derived['learned_context_rules'] if x['id'] == 'friction_to_automation')
        self.assertEqual(report['feedback_count'], 1)
        self.assertEqual(rule['preference']['feedback_count'], 1)
        self.assertEqual(rule['preference']['stage'], STAGE_SHADOW)

    def test_unknown_and_non_allowlisted_feedback_are_ignored(self):
        rows = [
            {'feedback_id':'a','rule_id':'missing','ratings':{a:2 for a in ('voice_fit','readability','factual_fidelity','task_fit')},'allow_preference_learning':True},
            {'feedback_id':'b','rule_id':'friction_to_automation','ratings':{a:2 for a in ('voice_fit','readability','factual_fidelity','task_fit')},'allow_preference_learning':False},
        ]
        _, report = apply_preference_feedback(learned_pack(), rows)
        self.assertEqual(report['feedback_count'], 0)
        self.assertEqual({x['reason'] for x in report['ignored']}, {'unknown_rule', 'not_allowlisted'})

    def test_free_text_feedback_is_rejected(self):
        data = {
            'feedback_id':'unsafe', 'rule_id':'friction_to_automation', 'surface':'journal',
            'ratings': {'voice_fit':2,'readability':2,'factual_fidelity':2,'task_fit':2},
            'allow_preference_learning': True, 'comment':'この文章は俺っぽい',
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'feedback.jsonl'
            p.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_feedback(p)

    def test_preference_pack_does_not_mutate_current_knowledge(self):
        learned = learned_pack()
        current_before = json.dumps(BASE, ensure_ascii=False, sort_keys=True)
        derived, _ = apply_preference_feedback(learned, load_feedback(FEEDBACK))
        self.assertEqual(current_before, json.dumps(BASE, ensure_ascii=False, sort_keys=True))
        self.assertFalse(derived['preference_loop']['active_is_auto_published'])

    def test_surface_scores_are_kept_separately(self):
        derived, _ = apply_preference_feedback(learned_pack(), load_feedback(FEEDBACK))
        rule = next(x for x in derived['learned_context_rules'] if x['id'] == 'friction_to_automation')
        self.assertEqual(set(rule['preference']['surface_scores']), {'journal', 'update', 'sns'})

    def test_dormant_rule_is_not_used_by_writer(self):
        derived, _ = apply_preference_feedback(learned_pack(), load_feedback(FEEDBACK))
        ev = Evidence(
            source_id='pref-e1', captured_at='2026-08-20T20:00:00+09:00', actor='tester',
            text='Improve knowledge writer mode', source_type='test',
            project_hint='FOUNDRY GROWTH ENGINE', raw_evidence_ref='commit:pref-e1',
        )
        update = build_update(ev, derived)
        dormant_context = next(x['public_context'] for x in derived['learned_context_rules'] if x['id'] == 'replaceable_personalization')
        self.assertNotIn(dormant_context, update.summary)


if __name__ == '__main__':
    unittest.main()
