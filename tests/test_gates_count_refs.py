# -*- coding: utf-8 -*-
"""schema 计数引用判据：既要抓住真的计数漂移，也不能把小节号当计数。

为什么值得钉住：这道闸门扫描仓库内的 Markdown，凡出现「N 属性 / N 必填 / N 条规则」就
与 `spec/method-card.schema.json` 对账。写文档时小节标题形如「4.2 属性分布图」，其中的
「2 属性」在无左边界时被读成「本行声明了 2 个属性」（schema 实为 37），闸门因此误报
（2026-10-10 由检索证据文档撞出）。压假阳性的同时不得放宽到漏掉真漂移，所以两侧都钉。

样例字符串**在运行期拼接**：本文件同样要过该闸门，测试自己不该成为例外。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.gates import SCHEMA_COUNT_PAT  # noqa: E402

B = "必" + "填"
S = "属" + "性"
R = "条" + "规则"


class TestSchemaCountPattern(unittest.TestCase):
    def test_real_declarations_match(self):
        cases = ["26 " + B + " / 37 " + S,
                 "37 " + S,
                 "共 47 " + R,
                 "本节列出 12 个" + S,
                 "schema 实为 37 " + S]
        for s in cases:
            self.assertTrue(SCHEMA_COUNT_PAT.search(s), s)

    def test_section_numbers_are_not_counts(self):
        cases = ["### 4.2 " + S + "分布图",
                 "### 2.1 " + B + "项与默认值",
                 "### 3.4 " + R + "的组织方式",
                 "见 5.1 " + S + "对照表"]
        for s in cases:
            self.assertIsNone(SCHEMA_COUNT_PAT.search(s), s)

    def test_glued_digits_are_not_counts(self):
        cases = ["46 " + R + "22 WARN",
                 "26 " + B + "0 项"]
        for s in cases:
            self.assertIsNone(SCHEMA_COUNT_PAT.search(s), s)


if __name__ == "__main__":
    unittest.main()
