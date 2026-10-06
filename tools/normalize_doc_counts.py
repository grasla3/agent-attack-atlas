#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全库文档里引用的 schema 计数统一到当前真值。

动因：`spec/method-card.schema.json` 每增删一个字段或一条规则，
**全库会有几十处「N 必填 / N 属性 / N 条规则」跟着过期**。
Gate 0 的 `card_contract_sync` 会逐处报错，但手工改不现实——本工具做归一。

**唯一真值源是 schema**；本工具只写数字，不动句子。

用法:
    python tools/normalize_doc_counts.py --dry-run
    python tools/normalize_doc_counts.py
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
#: 这些文件按设计会引用历史数字（变更提案、覆盖率表、规则索引），跳过
SKIP = {"docs/README.md", "ci-coverage.md", "rule-index.md"}

# `个?属性` 与 `个?必填` 都必须带「个?」——早期版本漏了属性分支，
# 导致「37 个属性」永远不被归一（踩过一次）。
# `(?!\d)` 用来排除「20 条规则22 WARN」这类「规则号」写法（被撞出过一次假阳性）。
PAT = re.compile(r"(\d+)(\s*)(个?必填|个?属性|条\s*`?x-validation-rules`?|条\s*校验规则|条规则|规则)(?!\d)")


def kind(tok: str) -> str:
    if "必填" in tok:
        return "必填"
    if "属性" in tok:
        return "属性"
    return "规则"


def main(argv=None):
    ap = argparse.ArgumentParser(description="schema 计数归一")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    S = json.loads((ROOT / "spec" / "method-card.schema.json").read_text(encoding="utf-8"))
    want = {"必填": len(S["required"]), "属性": len(S["properties"]),
            "规则": len(S["x-validation-rules"])}

    files = (list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md"))
             + list((ROOT / "项目说明").glob("*.md")) + list((ROOT / "spec").glob("*.md"))
             + list((ROOT / "tools").glob("*.py")))
    n_file = n_line = 0
    for p in files:
        if p.name in SKIP:
            continue
        lines = io.open(p, encoding="utf-8").read().split("\n")
        changed = False
        for i, ln in enumerate(lines):
            if "~~" in ln or "allow-count-drift" in ln:
                continue
            def sub(m):
                nonlocal changed
                k = kind(m.group(3))
                if int(m.group(1)) == want[k]:
                    return m.group(0)
                changed = True
                return "%d%s%s" % (want[k], m.group(2), m.group(3))
            new = PAT.sub(sub, ln)
            if new != ln:
                lines[i] = new
                n_line += 1
        if changed:
            n_file += 1
            print("  %s" % p.relative_to(ROOT))
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("%s：%d 个文件 / %d 行（真值 %d 必填 / %d 属性 / %d 条规则）"
          % ("待修" if a.dry_run else "已归一", n_file, n_line,
             want["必填"], want["属性"], want["规则"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())