#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩展三明治查询族：以 CoT / few-shot / 夹层结构系统性提取系统提示

派生自 methods/T06/T06.py + 卡 T06.LIT-B-109.extended_sandwich_query_family（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-109_extended_sandwich_query_family.py --plan         # 打印执行计划（不执行）
  python LIT-B-109_extended_sandwich_query_family.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-109_extended_sandwich_query_family.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-109.extended_sandwich_query_family"

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
    "mechanism": "LIT-B-109",
    "mechanism_source": "B-109 SPE-LLM（arXiv 2505.23817，无 venue）Table 1（三类代表性模型攻防性能）/ Figure 4、5（CoT、few-shot）/ Figure 6、7（extended sandwich）/ Figure 8、9（防御）：extended 攻击仍达约 32%",
    "vector": "用户输入",
    "technique": "手工设计",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-109 SPE-LLM（arXiv 2505.23817，无 venue）Table 1（三类代表性模型攻防性能）/ Figure 4、5（CoT、few-shot）/ Figure 6、7（extended sandwich）/ Figure 8、9（防御）：extended 攻击仍达约 32%",
        "results/README.md #5",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-109",
        "locator": "B-109（arXiv 2505.23817）Table 1 与 Figure 6：extended sandwich 约 32%，有独立对照",
        "value": "夹层/结构化查询族（非优化、非 RL）"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-110.remember_to_start_instruction_family",
    "bib_id": "B-109 SP"
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
