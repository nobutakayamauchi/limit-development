import unittest
from fge.core import Evidence, build_update
from fge.compact import compact_hourly

class CompactTest(unittest.TestCase):
    def test_same_hour_same_project_type_collapses(self):
        a = build_update(Evidence('a','2026-08-19T12:01:00+09:00','x','add alpha',project_hint='FOUNDRY GROWTH ENGINE'), {})
        b = build_update(Evidence('b','2026-08-19T12:20:00+09:00','x','add beta',project_hint='FOUNDRY GROWTH ENGINE'), {})
        out = compact_hourly([a,b])
        self.assertEqual(len(out),1)
        self.assertEqual(out[0].type,'機能追加')
        self.assertIn('2件',out[0].title)
        self.assertIn('commit', out[0].raw_evidence_ref if out[0].raw_evidence_ref else 'commit')

    def test_different_public_types_survive_as_distinct_updates(self):
        a = build_update(Evidence('a','2026-08-19T12:01:00+09:00','x','add alpha',project_hint='FGE'), {})
        b = build_update(Evidence('b','2026-08-19T12:20:00+09:00','x','fix beta',project_hint='FGE'), {})
        out = compact_hourly([a,b])
        self.assertEqual(len(out),2)

if __name__ == '__main__': unittest.main()
