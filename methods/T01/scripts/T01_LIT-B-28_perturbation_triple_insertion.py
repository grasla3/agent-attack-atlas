#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图谱三元组补链投毒：先定对抗目标答案，再插入扰动三元组补全误导推理链

派生自 methods/T01/T01.py + 卡 T01.LIT-B-28.perturbation_triple_insertion（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-28_perturbation_triple_insertion.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-28_perturbation_triple_insertion.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-28_perturbation_triple_insertion.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-28.perturbation_triple_insertion"

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
    "granularity": "单文档",
    "trigger": "常驻",
    "turns": 1,
    "custom_logic_required": False,
    "distinctness_axis": "mechanism_first_step"
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-28",
    "mechanism_source": "B-28 · Information Fusion 2026 · Vol 127 Part C · ArtNo 103900 · 题名 \"Exploring knowledge poisoning attacks to retrieval-augmented generation\"",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-28 Table/Fig（两个基准 × 四个 KG-RAG 方法上的性能退化）",
        "B-28 正文：最小 KG 扰动下仍显著降低 KG-RAG 性能"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-28",
        "locator": "B-28 (Information Fusion 2026, Vol 127, ArtNo 103900) 的扰动三元组构造与消融实验：图谱三元组补链为独立构造，与文本级投毒不同，有独立实验数字",
        "value": "LIT-B-28"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-27.reward_subspace_projection"
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
