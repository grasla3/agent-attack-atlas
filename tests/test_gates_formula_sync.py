# -*- coding: utf-8 -*-
"""门禁自身的自测 —— 特别是「规范 ↔ 实现 对账」这一项。

为什么要测门禁：本项目已经发生过三次「文档改了、实现没改」的事故。
一个从不失败的检查等于没有检查。因此这里同时断言：
  1. 当前仓库**通过**对账；
  2. 人为把规范改坏之后，对账**必须失败**（否则它是个装饰品）。
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import gates       # noqa: E402

REPO = pathlib.Path(gates.ROOT)


class TestFormulaSyncGate(unittest.TestCase):
    def test_repo_is_in_sync(self):
        r = gates.check_formula_sync()
        self.assertEqual(
            r.status, "pass",
            "规范与实现不一致：\n" + "\n".join("%s %s" % (f.path, f.message) for f in r.errors))

    def _drift(self, old: str, new: str) -> "gates.CheckResult":
        """在临时副本里把 spec/scoring.md 改坏，返回对账结果。"""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            (td / "spec").mkdir()
            doc = (REPO / "spec" / "scoring.md").read_text(encoding="utf-8")
            self.assertIn(old, doc, "测试锚点不存在：%r" % old)
            (td / "spec" / "scoring.md").write_text(
                doc.replace(old, new), encoding="utf-8", newline="\n")
            shutil.copytree(REPO / "score", td / "score")
            orig = gates.ROOT
            gates.ROOT = td
            try:
                return gates.check_formula_sync()
            finally:
                gates.ROOT = orig

    def test_detects_weight_drift(self):
        r = self._drift("| `W_REACH` 载体可达性 | 0.25 |",
                        "| `W_REACH` 载体可达性 | 0.35 |")
        self.assertEqual(r.status, "fail", "权重被改坏却没被发现")
        self.assertTrue(any("W_REACH" in f.message for f in r.errors))

    def test_detects_cap_drift(self):
        r = self._drift("`CAP_TEXT_ONLY=2.0`", "`CAP_TEXT_ONLY=5.0`")
        self.assertEqual(r.status, "fail", "封顶值被改坏却没被发现")
        self.assertTrue(any("CAP_TEXT_ONLY" in f.message for f in r.errors))

    def test_detects_physical_axis_drift(self):
        r = self._drift("| `D01` | 停用正常设备 | **9.00** |",
                        "| `D01` | 停用正常设备 | **1.00** |")
        self.assertEqual(r.status, "fail", "I_physical 表被改坏却没被发现")
        self.assertTrue(any("D01" in f.message for f in r.errors))

    def test_detects_l_to_i_mapping_drift(self):
        r = self._drift("| L3 | 不可逆，仅影响本用户 | **5.00** |",
                        "| L3 | 不可逆，仅影响本用户 | **8.00** |")
        self.assertEqual(r.status, "fail", "L→I_infosec 映射被改坏却没被发现")
        self.assertTrue(any("L3" in f.message for f in r.errors))


class TestGateExitCodes(unittest.TestCase):
    """docs/README.md D6 的退出码语义。"""

    def test_usage_error(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = gates.main(["--check", "no_such_check"])
        self.assertEqual(rc, gates.EXIT_USAGE)
        self.assertIn("未知检查", buf.getvalue())

    def test_list_ok(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = gates.main(["--list"])
        self.assertEqual(rc, gates.EXIT_OK)
        self.assertIn("formula_sync", buf.getvalue())      # 新检查已注册进 Gate 0


if __name__ == "__main__":
    unittest.main(verbosity=2)