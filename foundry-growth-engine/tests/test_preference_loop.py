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
SYNTHETIC_FEEDBACK = ROOT / 'tests/fixtures/preference-feedback.synthetic.jsonl'
PRODUCTION_FEEDBACK = ROOT / 'config/preference-feedback.limit-development.jsonl'


def learned_pack():
    return distill(load_jsonl(CHAT), BASE, RULES)[0]


def row(fid='x', rid='friction_to_automation', output='out-1', surface='journal', allow=True):
    return {
        'feedback_id': fid,
        'rule_id': rid,
        'surface': surface,
        'output_id': output,
        'ratings': {'voice_fit': 2, 'readability': 2, 'factual_fidelity': 2, 'task_fit': 2},
        'verdict': 'accept',
        'allow_preference_learning': allow,
    }


class PreferenceLoopTest(unittest.TestCase):
    def test_synthetic_fixture_exercises_active_shadow_and_dormant(self):
        derived, report = apply_preference_feedback(learned_pack(), load_feedback(SYNTHETIC_FEEDBACK))
        states = {x['id']: x['preference']['stage'] for x in derived['preference_rule_catalog']}
        self.assertEqual(states['friction_to_automation'], STAGE_ACTIVE)
        self.assertEqual(states['destination_over_link_success'], STAGE_SHADOW)
        self.assertEqual(states['replaceable_personalization'], STAGE_DORMANT)
        self.assertEqual(report['stage_counts'], {'SHADOW': 1, 'ACTIVE': 1, 'DORMANT': 1})
        usable = {x['id'] for x in derived['learned_context_rules']}
        self.assertNotIn('replaceable_personalization', usable)

    def test_production_ledger_starts_without_invented_preferences(self):
        feedback = load_feedback(PRODUCTION_FEEDBACK)
        self.assertEqual(feedback, [])
        derived, report = apply_preference_feedback(learned_pack(), feedback)
        self.assertEqual(report['stage_counts'], {'SHADOW': 3, 'ACTIVE': 0, 'DORMANT': 0})
        self.assertTrue(all(x['preference']['stage'] == STAGE_SHADOW for x in derived['learned_context_rules']))

    def test_no_feedback_stays_shadow(self):
        derived, _ = apply_preference_feedback(learned_pack(), [])
        self.assertTrue(all(x['preference']['stage'] == STAGE_SHADOW for x in derived['learned_context_rules']))

    def test_duplicate_feedback_id_counts_once(self):
        first = row('dup', output='same-output')
        derived, report = apply_preference_feedback(learned_pack(), [first, dict(first)])
        rule_state = next(x for x in derived['learned_context_rules'] if x['id'] == 'friction_to_automation')
        self.assertEqual(report['feedback_count'], 1)
        self.assertEqual(rule_state['preference']['feedback_count'], 1)
        self.assertEqual(rule_state['preference']['stage'], STAGE_SHADOW)

    def test_same_output_cannot_be_rated_repeatedly_to_force_promotion(self):
        rows = [row('a', output='same'), row('b', output='same'), row('c', output='same')]
        derived, report = apply_preference_feedback(learned_pack(), rows)
        state = next(x for x in derived['learned_context_rules'] if x['id'] == 'friction_to_automation')
        self.assertEqual(report['feedback_count'], 1)
        self.assertEqual(state['preference']['stage'], STAGE_SHADOW)
        self.assertEqual([x['reason'] for x in report['ignored']].count('duplicate_output'), 2)

    def test_surface_case_does_not_bypass_duplicate_output_guard(self):
        rows = [row('a', output='same', surface='Journal'), row('b', output='same', surface='journal')]
        _, report = apply_preference_feedback(learned_pack(), rows)
        self.assertEqual(report['feedback_count'], 1)
        self.assertEqual([x['reason'] for x in report['ignored']], ['duplicate_output'])

    def test_single_normal_negative_stays_shadow(self):
        negative = row('neg', rid='replaceable_personalization', output='negative-1', surface='technical')
        negative['ratings'] = {'voice_fit': -1, 'readability': 0, 'factual_fidelity': -1, 'task_fit': -1}
        negative['verdict'] = 'reject'
        derived, _ = apply_preference_feedback(learned_pack(), [negative])
        state = next(x for x in derived['preference_rule_catalog'] if x['id'] == 'replaceable_personalization')
        self.assertEqual(state['preference']['stage'], STAGE_SHADOW)

    def test_unknown_and_non_allowlisted_feedback_are_ignored(self):
        rows = [row('a', rid='missing'), row('b', allow=False, output='out-2')]
        _, report = apply_preference_feedback(learned_pack(), rows)
        self.assertEqual(report['feedback_count'], 0)
        self.assertEqual({x['reason'] for x in report['ignored']}, {'unknown_rule', 'not_allowlisted'})

    def test_free_text_feedback_is_rejected(self):
        data = row('unsafe')
        data['comment'] = 'この文章は俺っぽい'
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'feedback.jsonl'
            p.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_feedback(p)

    def test_missing_output_identity_is_rejected(self):
        data = row('missing-output')
        data.pop('output_id')
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'feedback.jsonl'
            p.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_feedback(p)

    def test_verdict_rating_conflict_is_rejected(self):
        data = row('conflict')
        data['verdict'] = 'reject'
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'feedback.jsonl'
            p.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_feedback(p)

    def test_preference_pack_does_not_mutate_current_knowledge(self):
        learned = learned_pack()
        current_before = json.dumps(BASE, ensure_ascii=False, sort_keys=True)
        derived, _ = apply_preference_feedback(learned, load_feedback(SYNTHETIC_FEEDBACK))
        self.assertEqual(current_before, json.dumps(BASE, ensure_ascii=False, sort_keys=True))
        self.assertFalse(derived['preference_loop']['active_is_auto_published'])

    def test_surface_scores_are_kept_separately(self):
        derived, _ = apply_preference_feedback(learned_pack(), load_feedback(SYNTHETIC_FEEDBACK))
        rule_state = next(x for x in derived['preference_rule_catalog'] if x['id'] == 'friction_to_automation')
        self.assertEqual(set(rule_state['preference']['surface_scores']), {'journal', 'update', 'sns'})

    def test_dormant_rule_is_not_used_by_writer(self):
        derived, _ = apply_preference_feedback(learned_pack(), load_feedback(SYNTHETIC_FEEDBACK))
        dormant_context = next(x['public_context'] for x in derived['preference_rule_catalog'] if x['id'] == 'replaceable_personalization')
        self.assertNotIn('replaceable_personalization', {x['id'] for x in derived['learned_context_rules']})
        ev = Evidence(
            source_id='pref-e1', captured_at='2026-08-20T20:00:00+09:00', actor='tester',
            text='Improve knowledge writer mode', source_type='test',
            project_hint='FOUNDRY GROWTH ENGINE', raw_evidence_ref='commit:pref-e1',
        )
        update = build_update(ev, derived)
        self.assertNotIn(dormant_context, update.summary)


if __name__ == '__main__':
    unittest.main()
