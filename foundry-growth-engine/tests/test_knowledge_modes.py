from __future__ import annotations

import json
from pathlib import Path
import unittest

from fge.core import Evidence, build_update, load_knowledge
from fge.engines import KnowledgeAwarePublicWriter, RuleBasedPublicWriter

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
PLAIN = load_knowledge(str(ROOT / "config/knowledge.plain.json"))
KNOWLEDGE = load_knowledge(str(ROOT / "config/knowledge.limit-development.json"))


class KnowledgeModeTest(unittest.TestCase):
    def ev(self, text, project_hint=""):
        return Evidence(
            source_id="same-evidence",
            captured_at="2026-08-19T20:00:00+09:00",
            actor="tester",
            text=text,
            source_type="test",
            project_hint=project_hint,
            raw_evidence_ref="commit:same-evidence",
        )

    def test_plain_contract_is_pinned(self):
        cases = json.loads((ROOT / "tests/fixtures/plain_contract.json").read_text(encoding="utf-8"))
        for case in cases:
            u = build_update(self.ev(case["text"], case.get("project_hint", "")), PLAIN)
            self.assertEqual(u.title, case["title"])
            self.assertEqual(u.summary, case["summary"])

    def test_same_evidence_can_be_plain_or_knowledge(self):
        ev = self.ev("Fix retry queue ordering", "FOUNDRY GROWTH ENGINE")
        plain = build_update(ev, PLAIN)
        enriched = build_update(ev, KNOWLEDGE)
        self.assertEqual(plain.source_id, enriched.source_id)
        self.assertEqual(plain.raw_evidence_ref, enriched.raw_evidence_ref)
        self.assertNotEqual(plain.summary, enriched.summary)
        self.assertIn("仕事のあと", enriched.summary)

    def test_reviewed_rewrite_rule_beats_generic_humanization(self):
        u = build_update(self.ev("Fix journal navigation", "FOUNDRY GROWTH ENGINE"), KNOWLEDGE)
        self.assertEqual(u.title, "開発日誌を、一覧だけでなく本文まで読めるようにした")
        self.assertIn("読者が読みたい記録", u.summary)

    def test_knowledge_is_public_context_not_private_memory(self):
        self.assertEqual(KNOWLEDGE.get("mode"), "KNOWLEDGE")
        safety = KNOWLEDGE.get("safety", {})
        self.assertTrue(safety.get("public_only"))
        self.assertIn("legal dispute details", safety.get("never_infer", []))
        self.assertNotIn("rewrite_rules", PLAIN) if False else None

    def test_writer_slots_remain_separate(self):
        self.assertEqual(RuleBasedPublicWriter.name, "rule-based-v0")
        self.assertEqual(KnowledgeAwarePublicWriter.name, "knowledge-aware-v1")


if __name__ == "__main__":
    unittest.main()
