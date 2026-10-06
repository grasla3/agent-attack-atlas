#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T07 派生脚本 · T07.LIT-B-126.loopllm_repetitive_generation

由 methods/T07/T07.py（类模块，手写） + 本卡参数**派生**而成（methods/T07/gen_finish.py）。
学生成器同一参数得到同一份（docs/delivery-form.md §1）。

用法：
  python methods/T07/scripts/T07_LIT-B-126_loopllm_repetitive_generation.py --plan            # 打印执行计划（不执行）
  python methods/T07/scripts/T07_LIT-B-126_loopllm_repetitive_generation.py --plan --grid     # 按维度档位展开

S4 / 禁令 9：本脚本**不含任何载荷正文**，args 里只有结构性参数
（入口 / 目标组件 / 探针类别 / 剂量 / 位置 / 轮次）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from T07 import build_plan, plan_grid, spec_from_card, validate  # noqa: E402

METHOD_ID = "T07.LIT-B-126.loopllm_repetitive_generation"
PARAMS = {"entry_point": "用户输入", "probe": "repetitive_generation", "cyclic_segment_length_grid": [2, 8, 32], "output_cap_grid": [1024, 4096], "turns": 1}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = spec_from_card(METHOD_ID)
    if "--validate" in argv:
        errs = validate(spec)
        print(json.dumps({"method_id": METHOD_ID, "ok": not errs, "errors": errs},
                         ensure_ascii=False, indent=1))
        return 0 if not errs else 1
    plans = plan_grid(spec) if "--grid" in argv else [build_plan(spec)]
    print(json.dumps(plans if "--grid" in argv else plans[0], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
