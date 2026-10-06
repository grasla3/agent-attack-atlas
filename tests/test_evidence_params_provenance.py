# -*- coding: utf-8 -*-
"""证据里的判据参数来源必须**如实记账**：标签写的是什么，参数里就得是什么。

## 为什么钉这两条

1. **占位符检测**（`harness/evidence.py` 的 `has_unresolved_placeholder`）：判据参数里若还留着
   `<read-at-runtime>` / `T06CANARY-<random32>` / `[待校准]` 这类模板，这条证据就复算不出它
   自己记的判定。检测器宁可从严——误判成占位符只是少声称一次，漏判才是把不可复算说成可复算。
2. **来源标签**（`harness/runner.py` 的 `resolve_judge_params`）：`params_for` 存在但**原样返回
   卡上声明**（`state_diff` 的真实形态）时，标签不得写成 `runtime`——那是"看着解析过、其实没解析"。
   实测缺陷：`batch-c97700f01a94` 的 10 个 `state_diff` 格曾如此；`batch-6d0b76397335` 则是记了
   模板却判 `pass`，trial 文件复算不出自己。

运行：`python -m unittest tests.test_evidence_params_provenance -v`
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import evidence as E  # noqa: E402
from harness import runner as R  # noqa: E402


class TestPlaceholderDetector(unittest.TestCase):
    """占位符检测器：**宁可从严**（误判成占位符只是少声称一次）。"""

    def test_catches_every_known_placeholder_shape(self):
        for v in ["<read-at-runtime>", "T06CANARY-<random32>", "[待校准]",
                  "sha256:baseline-svc_thin", "sha256:attacked-svc_thin"]:
            with self.subTest(v=v):
                self.assertTrue(E.has_unresolved_placeholder(v))

    def test_real_values_are_not_placeholders(self):
        for v in ["mcp_tool_registry", "description", 1.0, True, None, 0]:
            with self.subTest(v=v):
                self.assertFalse(E.has_unresolved_placeholder(v))

    def test_walks_nested_containers(self):
        self.assertTrue(E.has_unresolved_placeholder({"a": {"b": ["<x>"]}}))
        self.assertFalse(E.has_unresolved_placeholder({"a": {"b": ["fine"]}}))


class TestResolveJudgeParamsUsesATemplateLens(unittest.TestCase):
    class _JudgeEchoingDeclared:
        """`params_for` 存在、但**原样返回卡上声明**（`state_diff` 的真实形态）。"""
        judge_id = "state_diff"

        def params_for(self, card):
            return dict((card.get("judge") or {}).get("params") or {})

    class _JudgeResolving:
        judge_id = "prompt_leak"

        def params_for(self, card):
            p = dict((card.get("judge") or {}).get("params") or {})
            p["expected_verbatim"] = "INTERNAL-CANARY-runtime"
            return p

    class _JudgeWithoutParamsFor:
        judge_id = "x"

    def test_unchanged_params_are_not_labelled_runtime(self):
        card = {"judge": {"params": {"entity_id": "e", "before_state_hash": "<read-at-runtime>"}}}
        got, src = R.resolve_judge_params(self._JudgeEchoingDeclared(), card)
        self.assertEqual(src, "card_declared_unchanged")
        self.assertEqual(got["before_state_hash"], "<read-at-runtime>")

    def test_changed_params_are_labelled_runtime(self):
        card = {"judge": {"params": {"canary_id": "c", "expected_verbatim": "T06CANARY-<random32>"}}}
        got, src = R.resolve_judge_params(self._JudgeResolving(), card)
        self.assertEqual(src, "runtime")
        self.assertNotIn("<random32>", got["expected_verbatim"])

    def test_no_params_for_is_card_declared(self):
        got, src = R.resolve_judge_params(self._JudgeWithoutParamsFor(), {"judge": {"params": {"a": "b"}}})
        self.assertEqual((got, src), ({}, "card_declared"))


if __name__ == "__main__":
    unittest.main()