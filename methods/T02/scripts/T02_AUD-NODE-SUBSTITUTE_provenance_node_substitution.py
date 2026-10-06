#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""节点级溯源替换：把记录中的攻击节点换成语义相近的节点名以规避溯源检测

派生脚本 —— 由 methods/T02/T02.py（类模块）+ 本卡参数生成，**不是手写**。
重新生成：python methods/T02/gen_scripts.py

卡：        methods/T02/cards/T02_AUD-NODE-SUBSTITUTE_provenance_node_substitution.yaml
机制出处：  LIT-B-444（见 docs/domain-and-literature.md）
投放入口：  工具返回 -> log_ingest
证据层：    state（judge.verifier = audit_integrity）
篡改目标：  ['改写']
覆盖档位：  （由类模块 COVERAGE_GRID 给出）
参数来源：  card   ← card = 取自卡上/逐方法表；fallback:... = 回退（需人工确认）
不可参数化：是（见 T02.NON_PARAMETRIC）

S1 自足：读本文件 + 卡即可实现，不需回查文献。
S2 出处：构造对回卡上 provenance_components（见 plan 的 origin 字段）。
S3 可组合：档位经 --grid 展开，不硬编码。
S4 不夹带载荷正文：本文件不含任何载荷文本；本类多数方法的"操作"本身就是攻击。
S5 接口统一：与其他方法脚本同一套 CLI 与 exit code。

依赖：标准库 + pyyaml。无网络调用（NF2）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from T02 import build_plan, plan_grid, spec_from_card, validate  # noqa: E402

METHOD_ID = "T02.AUD-NODE-SUBSTITUTE.provenance_node_substitution"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='节点级溯源替换：把记录中的攻击节点换成语义相近的节点名以规避溯源检测')
    ap.add_argument("--grid", action="store_true", help="按 tamper_goal × coverage 档位展开（S3）")
    ap.add_argument("--dry-run", action="store_true", default=True, help="只产出计划（本交付形态不要求运行）")
    ap.add_argument("--out", help="把计划写到该路径（默认 stdout）")
    a = ap.parse_args(argv)

    spec = spec_from_card(METHOD_ID)
    errs = validate(spec)
    if errs:
        print("[FAIL] 构造规格不合格：", file=sys.stderr)
        for e in errs:
            print("   - %s" % e, file=sys.stderr)
        return 2

    plans = plan_grid(spec) if a.grid else [build_plan(spec, dry_run=a.dry_run)]
    text = json.dumps(plans if a.grid else plans[0], ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print("计划已写出：%s" % a.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
