#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双计数（`240 实例 / 去重方法数 N`）—— C4 + C8 的执行器。

`technical-design.md:122` 早已规划本文件，但一直未产出；在此之前
「去重方法数 N」只有纪律、没有执行器。

口径（`docs/judgment-discipline.md` C4 / `设计规格.md` §4.1）：
    五轴身份 = 注入入口 / 目标资产 / 机制首步 / 交互形态 / 判据层
    两张卡是同一方法 ⇔ 五轴全等
    在某轴上不同 ⇒ 计为两个方法，但须过 C11 举证（见 spec/method-card.schema.json 规则 42）

不做的事：不做任何推断。`dimensions` 档位、包装、标题一律不参与身份。

用法:
    python tools/count_identity.py
    python tools/count_identity.py --json
    python tools/count_identity.py --case T02
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import cardcheck as CC       # noqa: E402

# ── 历史规模目标。**已由 docs/README.md D14 取消**（2026-10-01）──
# 不再设「每类 30 / 共 240」，各类按文献饱和度如实收。
# 保留这两个常量只为一件事：让「方法-类别实例数」与「去重方法数 N」
# **仍然必须同报**（C8），并把 240 作为历史参照打印出来。
# **不得用它算缺口，也不得用它做任何达标判断。**
TARGET_INSTANCES = 240          # [已取消 · 仅作历史参照]
TARGET_PER_CASE = 30            # [已取消 · 仅作历史参照]


def compute(ctx: CC.Ctx) -> dict:
    real = ctx.real_cards
    axes = list(CC.C4_AXES.items())

    def key(c):
        return tuple(str(fn(c)) for _, fn in axes)

    by_case = {}
    for c in real:
        by_case.setdefault(c.get("case_id"), []).append(c)

    rows = []
    for case in sorted(x for x in by_case):
        cards = by_case[case]
        keys = {key(c) for c in cards}
        rows.append({
            "case_id": case,
            "cards": len(cards),
            "variants": len([c for c in ctx.cards if c.get("case_id") == case and c.get("variant_of")]),
            "distinct_methods": len(keys),
            "collapse": len(cards) - len(keys),
            "target": TARGET_PER_CASE,
            "shortfall": max(0, TARGET_PER_CASE - len(keys)),
            "mechanisms": len({c.get("mechanism_ref") for c in cards}),
        })

    all_keys = {key(c) for c in real}
    return {
        "instances": len(real),                 # 方法-类别实例数（= 非变体卡数）
        "distinct_methods": len(all_keys),      # 去重方法数 N
        "collapse": len(real) - len(all_keys),  # 跨类重合而塌缩掉的数量
        "target_instances": TARGET_INSTANCES,
        "target_per_case": TARGET_PER_CASE,
        "cards_total": len(ctx.cards),
        "variants_excluded": len(ctx.cards) - len(real),
        "by_case": rows,
        "axes": [ax for ax, _ in axes],
        "identity_rule": "C4 五轴全等即同一方法；轴差异须过 C11 举证",
    }


def render(res: dict) -> None:
    print("身份口径：%s" % res["identity_rule"])
    print("轴：%s" % " / ".join(res["axes"]))
    print()
    # D14（2026-10-01）：不再有「距 30」列——规模目标已取消，只报实测数。
    print("%-6s %6s %8s %10s %8s %8s" % (
        "类", "卡数", "变体", "去重方法数", "塌缩", "机制数"))
    print("-" * 62)
    for r in res["by_case"]:
        print("%-6s %6d %8d %10d %8d %8d" % (
            r["case_id"], r["cards"], r["variants"], r["distinct_methods"],
            r["collapse"], r["mechanisms"]))
    print("-" * 62)
    print("%-6s %6d %8d %10d %8d" % (
        "合计", res["cards_total"], res["variants_excluded"],
        res["distinct_methods"], res["collapse"]))
    print()
    print("方法-类别实例数 = %d（历史目标 %d，已由 D14 取消）" % (res["instances"], res["target_instances"]))
    print("去重方法数 N   = %d" % res["distinct_methods"])
    print()
    print("> **两个数必须同报，永远不得表述为「%d 种攻击方法」**（C8）。" % res["target_instances"])


def main(argv=None):
    ap = argparse.ArgumentParser(description="双计数（实例 / 去重方法数 N）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--case", default=None, help="只看某一类")
    a = ap.parse_args(argv)

    ctx = CC.Ctx(ROOT)
    res = compute(ctx)
    if a.case:
        res["by_case"] = [r for r in res["by_case"] if r["case_id"] == a.case]
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        render(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())