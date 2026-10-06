#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T04 派生脚本 · T04.B-66.objective_decoupled_backdoor

本文件由类模块 methods/T04/T04.py + 卡上参数**确定性派生**：同参数生成同一份。
它不手写任何构造逻辑 —— 构造逻辑只有一份，在类模块里。

来源（S2 有出处）：LIT-B-66，见卡 methods/T04/cards/T04_LIT-B-66_objective_decoupled_backdoor.yaml。
本脚本**不携带任何载荷正文**（S4 / 禁令 9）：只声明投放规格与判据面。

用法:
    python T04_LIT-B-66_objective_decoupled_backdoor.py --plan
    python T04_LIT-B-66_objective_decoupled_backdoor.py --plan --grid
"""
import argparse
import json
import sys
from pathlib import Path

# 控制台编码兜底：Windows 默认 GBK，而卡上的中文与箭头等字符会让 print 抛
# UnicodeEncodeError。必须在任何 print 之前设置（tools/ 下的脚本同样这么做）。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T04  # noqa: E402  （类模块）

METHOD_ID = "T04.B-66.objective_decoupled_backdoor"

#: 本方法的参数（与卡上 execution.args 一致）
PARAMS = {'attacker_capability': 'internal_component', 'paradigm': 'training_as_a_service', 'trigger_types': ['block', 'mug', 'stick'], 'suites': ['libero_10', 'libero_goal', 'libero_object', 'libero_spatial']}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true", help="输出执行计划（不执行）")
    ap.add_argument("--grid", action="store_true", help="按维度档位笛卡尔展开")
    ap.add_argument("--dry-run", action="store_true", default=True)
    a = ap.parse_args(argv)

    spec = T04.spec_from_card(METHOD_ID)
    spec.inducement.target_surface = PARAMS.get("target_surface", spec.inducement.target_surface)
    spec.inducement.control_tool = PARAMS.get("expected_control_tool", spec.inducement.control_tool)
    spec.attacker_capability = PARAMS.get("attacker_capability", spec.attacker_capability)

    errs = T04.validate(spec)
    if errs:
        print(json.dumps({"method_id": METHOD_ID, "structural_errors": errs},
                         ensure_ascii=False, indent=1))
        return 1

    plans = T04.plan_grid(spec) if a.grid else [T04.build_plan(spec, dry_run=a.dry_run)]
    print(json.dumps(plans if a.grid else plans[0], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
