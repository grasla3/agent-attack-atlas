#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记忆化诊断式提取：以困惑度与注意力直译路径解释并驱动提示提取

派生自 methods/T06/T06.py + 卡 T06.LIT-B-107.memorization_attention_path_analysis（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-107_memorization_attention_path_analysis.py --plan         # 打印执行计划（不执行）
  python LIT-B-107_memorization_attention_path_analysis.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-107_memorization_attention_path_analysis.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-107.memorization_attention_path_analysis"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "用户输入",
    "entry_tool": "user_turn",
    "artifact_kind": "text_only",
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
    "turns": 1,
    "dimensions": [
        "query_template",
        "probe_budget"
    ],
    "side_channel": False,
    "custom_logic_required": False
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-107",
    "mechanism_source": "B-107（arXiv 2408.02416，无 venue）Figure 1（模型规模）/ Figure 2（提示长度）/ Figure 4、5（困惑度）/ Figure 7（注意力可视化）/ Table 1（防御后评估）：提取率降 83.8% / 71.0%",
    "vector": "用户输入",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-107（arXiv 2408.02416，无 venue）Figure 1（模型规模）/ Figure 2（提示长度）/ Figure 4、5（困惑度）/ Figure 7（注意力可视化）/ Table 1（防御后评估）：提取率降 83.8% / 71.0%",
        "results/README.md #3",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-107",
        "locator": "B-107（arXiv 2408.02416）Figure 4/5 与 Table 1：困惑度与注意力路径有独立实验，降幅 83.8%/71.0%",
        "value": "对模型内部量（困惑度/注意力）的诊断式分析"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-108.rl_trained_attack_agent",
    "bib_id": "B-107（ar"
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
