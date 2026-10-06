# -*- coding: utf-8 -*-
"""G-25：`scope: approximation` 的两栏可机检化（`ROADMAP.md` G-25）。

**问题**：`scope` 回答「多忠实」，而任务书 §0.2 的「合格 ⇔ 载荷正文能在『不看目标』的
前提下写出来」是**另一个轴**上的二分。两件事装进同一个 `scope="approximation"` 桶之后，
报告按 `scope` 聚合就会说出「N 条 approximation 全部测过」——
**形式上正确、实质上误导**（与金丝雀判据 6/8 同形：数字对、构念错）。

**处置**：三个机器可读常量 + 证据层两栏（`harness/payloads.py` 的
`approximation_verdict()` / `testable_as_mechanism()` / `meta_of()`）。
**不加第三个 `scope` 取值** —— 那会把两个轴合并成一个。

运行：`python -m unittest tests.test_g25_approximation -v`
"""
from __future__ import annotations

import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from harness import payloads as P  # noqa: E402
from harness import runner as R  # noqa: E402

CASES = ["T0%d" % i for i in range(1, 9)]


def cards_of(cid):
    out = []
    for p in sorted(glob.glob(str(ROOT / "methods" / cid / "cards" / "*.yaml"))):
        with open(p, encoding="utf-8") as f:
            out.append(yaml.safe_load(f))
    return out


class TestConstantsExistAndPartition(unittest.TestCase):
    """八类都必须有三常量，且三者构成**硬分区**（这是 G-25 的机器可检形态）。"""

    def test_every_case_declares_the_three_constants(self):
        for cid in CASES:
            mod = R.load_class_module(cid)
            self.assertTrue(hasattr(mod, "BATCH_B_SCRIPT_HOOKS"), cid)
            self.assertTrue(hasattr(mod, "APPROXIMATION_VALID"), cid)
            self.assertTrue(hasattr(mod, "APPROXIMATION_NOT_VALID"), cid)

    def test_batch_b_equals_the_cards_marked_script_hook(self):
        """`BATCH_B_SCRIPT_HOOKS` 的语义 = 本类**全部** `execution.mode == script_hook` 的卡。

        ⚠️ T06 原先把它写成「乙批**新增**的 5 条」，与其余七类不同义（同一个字段名两种含义，
        D11）⇒ 2026-10-03 按八类统一定义改正为全部 7 条。本条把它钉死，防止再漂。
        """
        for cid in CASES:
            mod = R.load_class_module(cid)
            from_cards = {c["method_id"] for c in cards_of(cid)
                          if (c.get("execution") or {}).get("mode") == "script_hook"}
            self.assertEqual(set(mod.BATCH_B_SCRIPT_HOOKS), from_cards,
                             "%s：常量的集合必须等于卡上 mode==script_hook 的集合" % cid)

    def test_valid_and_not_valid_partition_batch_b(self):
        for cid in CASES:
            mod = R.load_class_module(cid)
            b = set(mod.BATCH_B_SCRIPT_HOOKS)
            v = set(mod.APPROXIMATION_VALID)
            n = set(mod.APPROXIMATION_NOT_VALID)
            self.assertFalse(v & n, "%s：两栏必须互斥" % cid)
            self.assertTrue(v <= b and n <= b, "%s：两栏都必须是 BATCH_B 的子集" % cid)
            self.assertEqual(b, v | n, "%s：BATCH_B = VALID ∪ NOT_VALID（无第三条路）" % cid)

    def test_not_valid_reasons_are_non_empty(self):
        """❌ 一栏必须带理由：只给一个方法名，报告里说不清"为什么测了也不是它"。"""
        for cid in CASES:
            mod = R.load_class_module(cid)
            for mid, why in (mod.APPROXIMATION_NOT_VALID or {}).items():
                self.assertTrue(str(why).strip(), "%s/%s 缺理由" % (cid, mid))


class TestEvidenceCarriesTheTwoColumns(unittest.TestCase):
    """证据层必须能分开两栏 —— 否则报告层拿不到分栏依据。"""

    def test_meta_reports_verdict_and_testability_for_every_card(self):
        seen = {"valid": 0, "not_valid": 0, "not_approximation": 0, "undetermined": 0}
        for cid in CASES:
            mod = R.load_class_module(cid)
            P.register_module_family(mod)
            for c in cards_of(cid):
                spec = P.spec_for_card(c, mod)
                meta = P.meta_of(spec)
                self.assertIn("testable_as_mechanism", meta)
                self.assertIn("approximation_verdict", meta)
                self.assertIn("artifact_in_payload", meta)
                verdict = meta["approximation_verdict"]
                seen[verdict] += 1
                # 两栏与"能不能当测量实例"必须一致，且**只有 valid 那一栏例外**
                if meta["scope"] == "approximation":
                    self.assertEqual(meta["testable_as_mechanism"], verdict == "valid",
                                     "%s：approximation 的 testable 必须等价于 valid" % c["method_id"])
                else:
                    self.assertTrue(meta["testable_as_mechanism"], c["method_id"])
        # 三类必须都出现过，否则本测试没验到东西（空集也能"通过"）
        self.assertGreater(seen["valid"], 0)
        self.assertGreater(seen["not_valid"], 0)
        self.assertGreater(seen["not_approximation"], 0)

    def test_batch_b_cards_are_never_undetermined(self):
        """**已判定的 61 条乙批卡一条都不许落进 `undetermined`** —— 那是标注缺口。"""
        bad = []
        for cid in CASES:
            mod = R.load_class_module(cid)
            P.register_module_family(mod)
            for c in cards_of(cid):
                if c["method_id"] not in set(mod.BATCH_B_SCRIPT_HOOKS):
                    continue
                meta = P.meta_of(P.spec_for_card(c, mod))
                if meta["approximation_verdict"] == "undetermined":
                    bad.append(c["method_id"])
        self.assertEqual(bad, [], "乙批卡落进 undetermined ⇒ 常量与规格脱节：%s" % bad)

    def test_undetermined_is_not_silently_read_as_valid(self):
        """`undetermined` **不得**默认成 `valid`（那正是 G-25 那个病的形状）。"""
        from harness.payloads import PayloadSpec
        spec = PayloadSpec(frame="behavioral_probe", scope="approximation")
        self.assertEqual(P.approximation_verdict(spec), "undetermined")
        self.assertFalse(P.testable_as_mechanism(spec))

    def test_generic_fallback_is_not_confused_with_testability(self):
        """`scope="generic"`（兜底探针）在**本轴**上是 True：回答"不是该方法"的是 `scope` 那一栏。"""
        spec = P.default_spec({"method_id": "TX.nope", "mechanism_ref": "X"})
        self.assertEqual(spec.scope, "generic")
        self.assertEqual(P.approximation_verdict(spec), "not_approximation")
        self.assertTrue(P.testable_as_mechanism(spec))


if __name__ == "__main__":
    unittest.main()
