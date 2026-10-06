#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自演化技能探测：UCB 技能排序 + 分层技能库在线探索提取系统提示

派生自 methods/T06/T06.py + 卡 T06.LIT-B-112.ucb_skill_evolution_probing（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-112_ucb_skill_evolution_probing.py --plan         # 打印执行计划（不执行）
  python LIT-B-112_ucb_skill_evolution_probing.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-112_ucb_skill_evolution_probing.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-112.ucb_skill_evolution_probing"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "用户输入",
    "entry_tool": "user_turn",
    "artifact_kind": "tool_return",
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
    "mechanism": "LIT-B-112",
    "mechanism_source": "B-112 Just Ask（ICML 2026）Figure 1（与反推真值对比，语义相似度 0.94）/ Table 2（结构成分回收）/ Table 3（按权重可得性）/ Table 4（安全策略覆盖）：分层技能库 14 原子探针 + 14 编排策略，100% 提取成功",
    "vector": "用户输入",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-112 Just Ask（ICML 2026）Figure 1（与反推真值对比，语义相似度 0.94）/ Table 2（结构成分回收）/ Table 3（按权重可得性）/ Table 4（安全策略覆盖）：分层技能库 14 原子探针 + 14 编排策略，100% 提取成功",
        "results/README.md #8",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-112",
        "locator": "B-112（ICML 2026）Table 3/4 与 Figure 1：41 个商用模型上 100% 提取成功，语义相似度 0.94（有反推真值对照）",
        "value": "UCB 在线探索 + 分层技能库自演化"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-113B.semantic_cache_side_channel",
    "bib_id": "B-112 Ju"
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
