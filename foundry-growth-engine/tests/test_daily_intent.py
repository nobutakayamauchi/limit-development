from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from fge.daily_intent import load_daily_intents, resolve_daily_intent


class DailyIntentTest(unittest.TestCase):
    def write(self, rows):
        td = tempfile.TemporaryDirectory()
        p = Path(td.name) / 'intents.jsonl'
        p.write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n', encoding='utf-8')
        return td, p

    def base(self, **overrides):
        row = {
            'observation_id':'o1','date':'2026-08-20','project':'FOUNDRY GROWTH ENGINE',
            'intent':'日誌で狙いと実作業を分けて読めるようにする。','source_type':'goal',
            'approval_status':'approved','public_safe':True,'allow_journal':True,'source_ref':'approved-chat-goal:2026-08-20'
        }
        row.update(overrides)
        return row

    def test_only_explicitly_approved_public_safe_records_load(self):
        rows = [
            self.base(observation_id='ok'),
            self.base(observation_id='pending', approval_status='pending'),
            self.base(observation_id='private', public_safe=False),
            self.base(observation_id='no-journal', allow_journal=False),
        ]
        td, p = self.write(rows)
        try:
            loaded = load_daily_intents(p)
            self.assertEqual([x['observation_id'] for x in loaded], ['ok'])
        finally:
            td.cleanup()

    def test_free_form_extra_fields_are_rejected(self):
        row = self.base(comment='raw chat should not be stored here')
        td, p = self.write([row])
        try:
            with self.assertRaises(ValueError):
                load_daily_intents(p)
        finally:
            td.cleanup()

    def test_source_ref_is_required_for_provenance(self):
        row = self.base()
        row.pop('source_ref')
        td, p = self.write([row])
        try:
            with self.assertRaises(ValueError):
                load_daily_intents(p)
        finally:
            td.cleanup()

    def test_old_intent_never_leaks_into_new_day(self):
        intents = [self.base()]
        self.assertIsNone(resolve_daily_intent(intents, '2026-08-21', 'FOUNDRY GROWTH ENGINE'))

    def test_repo_alias_can_match_public_project_intent(self):
        intents = [self.base(project='WebAI Bridge')]
        knowledge = {'project_aliases':[{'pattern':'webai bridge|web ai bridge','project':'WebAI Bridge'}]}
        found = resolve_daily_intent(intents, '2026-08-20', 'WebAI-Bridge', knowledge=knowledge)
        self.assertIsNotNone(found)
        self.assertEqual(found['project'], 'WebAI Bridge')


if __name__ == '__main__':
    unittest.main()
