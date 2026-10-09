# -*- coding: utf-8 -*-
"""凭据闸门的 OpenAI key 判据：既要抓住真 key，也不能把普通标识符里的 `sk-` 当 key。

为什么值得钉住：这道闸门扫描检索档案与证据 JSON，而代码检索的原始响应里带着他人仓库的
文件路径——`docs/studies/task-conditioned-least-privilege-head-to-head.md` 含子串 `sk-`，
在无左边界时被报成 "OpenAI 风格 API key"（2026-10-06 实测假阳性）。压假阳性的同时不得
放宽到漏掉真 key，所以两侧都钉。

样例字符串**在运行期拼接**：本文件也要过 `secrets` 闸门，测试自己不该成为例外。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.gates import SECRET_PATTERNS  # noqa: E402

KEY = [pat for pat, label in SECRET_PATTERNS if label == "OpenAI 风格 API key"][0]
P = "sk" + "-"


class TestOpenAIKeyPattern(unittest.TestCase):
    def test_real_keys_are_caught(self):
        cases = [P + "a" * 40,
                 P + "proj-" + "B" * 48,
                 '"' + P + "C" * 24 + '"',
                 "OPENAI_API_KEY=" + P + "d" * 32]
        for s in cases:
            self.assertTrue(KEY.search(s), s)

    def test_ordinary_identifiers_are_not_keys(self):
        cases = ["docs/studies/ta" + P + "conditioned-least-privilege-head-to-head.md",
                 "ta" + P + "conditioned-least-privilege-head-to-head",
                 "ri" + P + "assessment.md",
                 "ta" + P + "force-summary.json"]
        for s in cases:
            self.assertIsNone(KEY.search(s), s)


if __name__ == "__main__":
    unittest.main()
