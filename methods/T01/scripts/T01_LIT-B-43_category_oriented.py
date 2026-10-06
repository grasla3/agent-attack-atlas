#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""类别定向投毒：以一个目标函数覆盖整个查询类别，同时保持无关查询准确

派生自 methods/T01/T01.py + 卡 T01.LIT-B-43.category_oriented（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-43_category_oriented.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-43_category_oriented.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-43_category_oriented.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-43.category_oriented"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "检索文档",
    "write_tool": "kb_write",
    "artifact_kind": "kb_doc",
    "budget_grid": [
        1,
        3,
        5
    ],
    "placement_grid": [
        "corpus_head",
        "corpus_tail",
        "scattered"
    ],
    "granularity": "片段分解",
    "trigger": "常驻",
    "turns": 1,
    "custom_logic_required": False,
    "distinctness_axis": "mechanism_first_step"
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-43",
    "mechanism_source": "B-43 · IEEE TrustCom 2025 · pp.2181-2189 · DOI 10.1109/trustcom66490.2025.00254 · 题名 \"CatPoison: Category-Oriented Knowledge Poisoning Attacks in Retrieval-Augmented Generation Systems\"",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-43 原表（类别级 vs 实例级投毒的效果与无关查询准确率对比）",
        "B-43 正文：以优化问题形式化类别级目标，无关查询保持准确"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-43",
        "locator": "B-43 (TrustCom 2025, pp.2181-2189) 将投毒形式化为类别级优化问题，与实例级（单查询）构造为两次独立构造，各有独立实验",
        "value": "LIT-B-43"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-39.single_doc_adversarial_cot"
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T01.spec_from_card(METHOD_ID)
    spec.injection.budget_grid = PARAMS["budget_grid"]
    spec.injection.placement_grid = PARAMS["placement_grid"]

    if "--params" in argv:
        print(json.dumps({"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        plans = T01.plan_grid(spec) if "--grid" in argv else [T01.build_plan(spec)]
        print(json.dumps(plans if "--grid" in argv else plans[0],
                         ensure_ascii=False, indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
