#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RL 攻击智能体：以强化学习学出提示提取查询策略

派生自 methods/T06/T06.py + 卡 T06.LIT-B-108.rl_trained_attack_agent（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-108_rl_trained_attack_agent.py --plan         # 打印执行计划（不执行）
  python LIT-B-108_rl_trained_attack_agent.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-108_rl_trained_attack_agent.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-108.rl_trained_attack_agent"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "用户输入",
    "entry_tool": "user_turn",
    "artifact_kind": "chat_log",
    "budget_grid": [
        1,
        10,
        50
    ],
    "turns_grid": [
        1,
        3,
        5
    ],
    "turns": 3,
    "dimensions": [
        "query_template",
        "probe_budget",
        "turns"
    ],
    "side_channel": False,
    "custom_logic_required": True
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-108",
    "mechanism_source": "B-108 LeakAgent（COLM 2025）Table 1（相似度）/ Table 3（ASR）/ Table 4（对防御）/ Figure 1、2（奖励与消融）/ Figure 4（跨模型迁移）/ Table 5（效用）",
    "vector": "用户输入",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-108 LeakAgent（COLM 2025）Table 1（相似度）/ Table 3（ASR）/ Table 4（对防御）/ Figure 1、2（奖励与消融）/ Figure 4（跨模型迁移）/ Table 5（效用）",
        "results/README.md #4",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-108",
        "locator": "B-108 LeakAgent（COLM 2025）Table 3 与 Figure 2：ASR 与消融均有独立实验数字",
        "value": "RL 训练攻击 agent（细粒度奖励）"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-109.extended_sandwich_query_family",
    "bib_id": "B-108 Le"
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T06.spec_from_card(METHOD_ID)
    spec.probe.budget = PARAMS["budget_grid"][0]
    spec.turns_grid = PARAMS["turns_grid"]

    if "--params" in argv:
        print(json.dumps({"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        print(json.dumps(T06.plan_grid(spec) if "--grid" in argv else T06.build_plan(spec),
                         ensure_ascii=False, indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
