# -*- coding: utf-8 -*-
"""绝对路径闸门的判据本身：既要抓住真路径，也不能把转义序列当路径。

为什么值得钉住：这道闸门扫描 `results/trials/` 下上千个证据 JSON。证据正文里满是模型
自己写的 `word:\n- 条目`（在 JSON 里是 `word:\\n- `）。若模式把"盘符 + 反斜杠 + 两个字符"
一律当路径，闸门会被假阳性淹没；而一旦为了压假阳性把模式删掉，真实的本地路径就会随包
外泄。两种失效都发生过，所以这里两侧都钉。

样例字符串**在运行期拼接**（不写字面量）：本文件同样要过 `abs_paths` 闸门，
而闸门对代码文件是 ERROR 级——测试自己不该成为例外。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.gates import ABS_PATH_PATTERNS  # noqa: E402

WINDOWS = [pat for pat, label in ABS_PATH_PATTERNS if label == "Windows 绝对路径"][0]
B = chr(92)          # 单个反斜杠
BB = B + B           # JSON 转义后的一个反斜杠


class TestWindowsPattern(unittest.TestCase):
    def test_real_escaped_paths_are_caught(self):
        cases = [B.join(["D:", "", "attack", "", "electric", "", "exec"]),
                 B.join(["C:", "", "Users", "", "someone", "", "file.txt"]),
                 B.join(["D:", "", "ab", "", "cd"]),
                 B.join(["E:", "", "work", "", "notes.md"])]
        for s in cases:
            self.assertTrue(WINDOWS.search(s), s)

    def test_escape_sequences_are_not_paths(self):
        cases = ["format:" + BB + "n{" + BB + '"type' + BB + '": ' + BB + '"event' + BB + '"',
                 "password:" + BB + "n" + BB + "n[Reset Password]",
                 "points:" + BB + "n- Project timeline",
                 "Dear Client," + BB + "n" + BB + "nThank you"]
        for s in cases:
            self.assertIsNone(WINDOWS.search(s), s)


if __name__ == "__main__":
    unittest.main()