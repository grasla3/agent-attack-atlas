#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 docs/ci-coverage.md（唯一真相源是 tools/cardcheck.py 的 RULES 表）。

原先这个生成逻辑只存在于一次性脚本里，导致文档与代码脱节后**没人能重新生成**。
现固化为工具；Gate 0 的 ci_coverage_sync 断言产物与代码一致。

用法:
    python tools/gen_ci_coverage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import cardcheck as CC       # noqa: E402

UNBLOCK = {
    17: "`targets/` 下出现第一份 TargetProfile 时（当前报 INFO，不判通过）",
    18: "报告器落地时（设计规格 F5，二期）",
    19: "报告器落地时（设计规格 F5，二期）",
    20: "报告索引落地时（设计规格 F5，二期）",
}


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def main():
    ctx = CC.Ctx(ROOT)
    rules = ctx.schema["x-validation-rules"]
    cov = CC.coverage(ctx)
    assert not cov["missing"] and not cov["extra"], cov

    impl, struct, defer = [], [], []
    for i in sorted(CC.RULES):
        rid, _fn, status, why = CC.RULES[i]
        row = (i, rid, esc(rules[i - 1]), esc(why or ""))
        (impl if status == "implemented" else
         struct if status == "structural" else defer).append(row)

    # 正向覆盖：哪些规则号在 tests/fixtures/cards 里有反例
    covered = set()
    exp = ROOT / "tests" / "fixtures" / "cards" / "expectations.json"
    if exp.exists():
        import json
        for c in json.loads(exp.read_text(encoding="utf-8"))["cases"]:
            if c.get("expect_rule"):
                covered.add(c["expect_rule"])

    L = []
    A = L.append
    A("# 校验规则实现覆盖率（`docs/ci-coverage.md`）")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 生成方式 | **由 `tools/gen_ci_coverage.py` 从 `tools/cardcheck.py` 的 `RULES` 表生成**，不是手写 |")
    A("| 一致性 | Gate 0 `ci_coverage_sync` 断言本文件与代码一致；不一致即构建失败 |")
    A("| 规则来源 | `spec/method-card.schema.json` 的 `x-validation-rules`，共 **%d** 条 |" % cov["declared"])
    A("| 已实现 | **%d** 条（有可执行检查） |" % len(impl))
    A("| 结构保证 | **%d** 条（由 schema 的 type/enum/pattern/required 直接保证） |" % len(struct))
    A("| **登记缺口** | **%d** 条（下表逐条给出原因与解除条件） |" % len(defer))
    A("| 未映射 | %s |" % (", ".join(map(str, cov["missing"])) or "**无**"))
    A("")
    A("> **为什么要有这张表**：设计规格 F6 的 DoD 写着「任何一条 `x-validation-rules` 若尚未实现，必须在 `docs/ci-coverage.md` 显式列为缺口」。")
    A("> 只把规则写在 schema 里、却没有任何执行器，等于没有规则——本项目已经因为「Gate 1 全是 `[TODO]` 占位」")
    A("> 而漏掉过一次真实的契约冲突（`primary_asset` / `provenance_components` / `preconditions` 三处）。")
    A("")
    A("## 1. 已实现（%d 条）" % len(impl))
    A("")
    A("| # | rule_id | 规则摘要 | fixture 反例 |")
    A("|---|---|---|---|")
    for i, rid, txt, _ in impl:
        A("| %d | `%s` | %s | %s |" % (i, rid, txt[:100], "✅" if i in covered else "—"))
    A("")
    A("## 2. 由 schema 结构直接保证（%d 条）" % len(struct))
    A("")
    A("| # | rule_id | 规则摘要 | 由什么保证 |")
    A("|---|---|---|---|")
    for i, rid, txt, why in struct:
        A("| %d | `%s` | %s | %s |" % (i, rid, txt[:80], why))
    A("")
    A("## 3. 登记缺口（%d 条）" % len(defer))
    A("")
    A("| # | rule_id | 规则摘要 | 为什么现在实现不了 | 解除条件 |")
    A("|---|---|---|---|---|")
    for i, rid, txt, why in defer:
        A("| %d | `%s` | %s | %s | %s |" % (i, rid, txt[:80], why, UNBLOCK.get(i, "——")))
    A("")
    A("## 4. 部分实现的规则（主检查已实现，仍有一处待补）")
    A("")
    A("| # | rule_id | 已实现什么 | 还缺什么 |")
    A("|---|---|---|---|")
    for i in (4, 26):
        rid, _fn, _st, why = CC.RULES[i]
        A("| %d | `%s` | 结构与枚举层面的检查 | %s |" % (i, rid, why))
    A("")
    A("## 5. 正反用例")
    A("")
    A("`tests/fixtures/cards/` 下有 **1 套合法 + N 套违规**，每套只破坏一处；生成器是 `tools/gen_card_fixtures.py`。")
    A("Gate 1 的 `card_fixtures` 断言：违规样本**全部被拒**、合法样本**通过**。")
    A("")
    A("为什么这是必需的：`methods/` 为空时，所有规则都「通过」——因为无事可做。**一个从不失败的检查等于没有检查。**")
    A("")

    out = ROOT / "docs" / "ci-coverage.md"
    out.write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("wrote %s  (%d B)" % (out.name, out.stat().st_size))
    print("声明 %d：已实现 %d / 结构 %d / 缺口 %d；其中有 fixture 反例的 %d 条"
          % (cov["declared"], len(impl), len(struct), len(defer), len(covered)))


if __name__ == "__main__":
    sys.exit(main())