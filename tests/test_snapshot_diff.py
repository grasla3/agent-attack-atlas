# -*- coding: utf-8 -*-
"""回退工具的自测。

背景（一个真实 bug）：`snapshot.py --diff <tag>` 原先只读
`<tag>:gate-manifest.json`，而该文件被 `.gitignore` 忽略 —— **任何 tag 里都没有它**，
于是 `--diff` 永远返回 1。回退工具在最需要它的时候是不可用的。

这里锁住修复：比对必须以 **git 树**为准，不依赖被忽略的清单文件。
"""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import snapshot      # noqa: E402


def _capture(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = snapshot.main(argv)
    return rc, buf.getvalue()


class TestSnapshotDiff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not snapshot.is_repo():
            raise unittest.SkipTest("不是 git 仓库")

    def test_diff_against_head_succeeds(self):
        rc, out = _capture(["--diff", "HEAD"])
        self.assertEqual(rc, 0, out)
        self.assertIn("新增", out)
        self.assertIn("回退到该快照", out)

    def test_diff_does_not_require_manifest(self):
        """回归：清单文件不在 git 里，比对也必须成功。"""
        rc, out = _capture(["--diff", "HEAD"])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("没有 gate-manifest.json", out)
        self.assertNotIn("不存在", out)

    def test_unknown_tag_fails_cleanly(self):
        rc, out = _capture(["--diff", "no-such-tag-xyzzy"])
        self.assertEqual(rc, 1)
        self.assertIn("不存在", out)

    def test_diff_reports_uncommitted_work(self):
        _, out = _capture(["--diff", "HEAD"])
        self.assertIn("工作区未提交", out)

    def test_oldest_tag_is_diffable_if_any(self):
        """对**最早**的 tag 也要能比对（旧 tag 最可能没有清单）。"""
        r = subprocess.run(["git", "tag", "-l", "--sort=creatordate"],
                           cwd=str(snapshot.ROOT), capture_output=True, text=True)
        tags = [t for t in r.stdout.split() if t.strip()]
        if not tags:
            self.skipTest("仓库里还没有 tag")
        rc, out = _capture(["--diff", tags[0]])
        self.assertEqual(rc, 0, out)


class TestSnapshotList(unittest.TestCase):
    def test_list_runs(self):
        rc, out = _capture(["--list"])
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)