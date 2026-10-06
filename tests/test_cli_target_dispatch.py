# -*- coding: utf-8 -*-
"""靶标分派的**登记一致性**（T08 接线暴露的缺口）。

## 为什么有这条测试

`harness/adapters/` 里加了 banking/travel 两个适配器、`targets/` 里也加了两份画像，
但 `harness/cli.py` 的 `cmd_run` 当时是**写死的 if/else**，只认 `agentdojo-workspace`
⇒ 新靶标"在库里、却一条命令都跑不起来"，而**没有任何测试会红**。
这正是本项目反复撞的形状：**东西齐了、接线没接，报告上看不出来**。

本文件钉三件事：
1. `cli._ADAPTERS` 里的每一项都能**真的 import 到那个类**；
2. `targets/*.json` 里每个 `target_id`（除纯纸面画像外）**要么**在分派表里、**要么**在
   `PAPER_ONLY` 白名单里并写明理由 —— 防止"加了画像忘了接线"或反之；
3. `python -m harness.cli targets` 能列出画像，且分派表里的 id 都是画像里有的。

运行：`python -m unittest tests.test_cli_target_dispatch -v`
"""
from __future__ import annotations

import importlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import cli  # noqa: E402

#: **纸面画像**：只用于先验分（`spec/prior.md` 的 V6 适用性），**没有**可跑适配器。
#: 每一项必须写清为什么它是纸面的 —— 不许默认放行（否则本测试就白设了）。
PAPER_ONLY = {
    "injecagent-toolkits": "从上游仓库导出的工具面画像；上游是基准数据集，无可执行靶场（见 results/README.md）",
    "poisonedrag-rag-pipeline": "PoisonedRAG 的 RAG 管线画像；接成可执行靶标尚未做（同上）",
}


def _adapters():
    return getattr(cli, "_ADAPTERS", None)


class TestDispatchTable(unittest.TestCase):
    def test_table_exists(self):
        self.assertIsInstance(_adapters(), dict, "cli._ADAPTERS 不存在 ⇒ 又回到写死分派了")

    def test_every_entry_imports(self):
        for tid, (mod, cls) in (_adapters() or {}).items():
            with self.subTest(target=tid):
                m = importlib.import_module(mod)
                self.assertTrue(hasattr(m, cls), "%s 里没有类 %s" % (mod, cls))

    def test_every_profile_is_either_wired_or_declared_paper_only(self):
        table = set((_adapters() or {}))
        paper = set(PAPER_ONLY)
        missing = []
        for p in sorted((ROOT / "targets").glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            tid = d.get("target_id")
            if not tid:
                continue
            if tid not in table and tid not in paper:
                missing.append((p.name, tid))
        self.assertEqual(missing, [],
                         "这些画像既不在 cli._ADAPTERS 也不在 PAPER_ONLY 里 ⇒ 要么接线、要么写明它为什么是纸面的：%s"
                         % missing)

    def test_wired_targets_have_profiles(self):
        have = set()
        for p in sorted((ROOT / "targets").glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("target_id"):
                have.add(d["target_id"])
        for tid in (_adapters() or {}):
            self.assertIn(tid, have, "分派表里的 %s 没有 targets/*.json 画像" % tid)

    def test_paper_only_entries_carry_a_reason(self):
        for tid, why in PAPER_ONLY.items():
            self.assertTrue(str(why).strip(), tid)


class TestTargetsCommand(unittest.TestCase):
    def test_cli_targets_lists_profiles(self):
        """`python -m harness.cli targets` 不得抛异常（它是用户发现靶标清单的入口）。"""
        self.assertEqual(cli.cmd_targets(None), 0)


if __name__ == "__main__":
    unittest.main()
