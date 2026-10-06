# -*- coding: utf-8 -*-
"""`tools/rescore.py`：离线复算必须与证据自述一致，给不出结论时必须报出来。

为什么值得钉住：`results/README.md` 向读者承诺"读数可离线复算"。这条承诺一旦悄悄失效
（判据改了、证据束字段丢了、聚合成"只在可用子集上算率"），报告看上去不会有任何变化。
本文件就是那条承诺的回归测试。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import rescore as RS  # noqa: E402


class TestAggregateRule(unittest.TestCase):
    """聚合口径必须与 `harness/runner.py` 一致：一次不可判则整格不给率。"""

    def test_paired_difference_is_adv_hat(self):
        c = RS.aggregate(["pass", "pass", "fail", "fail"], ["fail"] * 4)
        self.assertAlmostEqual(c["v_adv"], 0.5)
        self.assertAlmostEqual(c["v_ctrl"], 0.0)
        self.assertAlmostEqual(c["adv_hat"], 0.5)
        self.assertEqual(c["six_state"], "pass")

    def test_one_inconclusive_kills_the_rate(self):
        c = RS.aggregate(["pass", "pass", "inconclusive"], ["fail"] * 3)
        self.assertEqual(c["six_state"], "inconclusive")
        self.assertIsNone(c["adv_hat"])
        self.assertIsNone(c["v_adv"])

    def test_all_untested_is_not_fail(self):
        c = RS.aggregate(["untested"] * 3, ["untested"] * 3)
        self.assertEqual(c["six_state"], "untested")
        self.assertIsNone(c["adv_hat"])


class TestIntervals(unittest.TestCase):
    """区间口径：Wilson 与证据一致，Newcombe 与公告数字一致。"""

    def test_wilson_matches_the_evidence_field(self):
        got = RS.wilson(4, 5)
        self.assertAlmostEqual(got[0], 0.3755282641185388, places=9)
        self.assertAlmostEqual(got[1], 0.9637768390302125, places=9)

    def test_newcombe_excludes_zero_for_the_headline_cells(self):
        lo, hi, d = RS.newcombe_diff(4, 5, 0, 5)          # T02：4/5 vs 0/5
        self.assertAlmostEqual(d, 0.8)
        self.assertAlmostEqual(lo, 0.193, places=3)
        self.assertAlmostEqual(hi, 0.964, places=3)
        self.assertGreater(lo, 0.0)
        lo2, hi2, d2 = RS.newcombe_diff(6, 10, 0, 10)     # T03：6/10 vs 0/10
        self.assertAlmostEqual(d2, 0.6)
        self.assertAlmostEqual(lo2, 0.201, places=3)
        self.assertAlmostEqual(hi2, 0.832, places=3)

    def test_no_difference_gives_interval_covering_zero(self):
        lo, hi, d = RS.newcombe_diff(3, 10, 3, 10)
        self.assertAlmostEqual(d, 0.0)
        self.assertLess(lo, 0.0)
        self.assertGreater(hi, 0.0)


class TestShippedEvidenceReproduces(unittest.TestCase):
    """随包证据必须复算得出它自己记的判定。"""

    def test_headline_t03_cell(self):
        cells = RS.rescore_batch("batch-52ab975ca245", ROOT / "results" / "trials")
        cell = [c for k, c in cells.items() if k.startswith("T03.B-47")][0]
        self.assertTrue(cell["covered"])
        self.assertTrue(cell["matched"], cell["mismatches"][:2])
        self.assertAlmostEqual(cell["adv_hat"], 0.600, places=6)
        self.assertEqual(cell["six_state"], "pass")

    def test_live_readback_judge_is_refused_not_silently_passed(self):
        """该判据要活靶标读回：必须返回 None + 原因，不能被当成"复现成功"。"""
        got, why = RS.rescore_trial({"judge_id": "audit_integrity", "verdict": "pass"})
        self.assertIsNone(got)
        self.assertIn("读回", why)

    def test_missing_resolved_params_is_refused(self):
        got, why = RS.rescore_trial({"judge_id": "scenario_contract",
                                     "judge_params": {"case_id": "T03"},
                                     "judge_params_resolved": {}})
        self.assertIsNone(got)
        self.assertIn("judge_params_resolved", why)


if __name__ == "__main__":
    unittest.main()