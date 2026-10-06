#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图谱拓扑完整性攻击：不改文本内容，只破坏社区检测与关系过滤所依赖的拓扑结构

派生自 methods/T01/T01.py + 卡 T01.LIT-B-37.graph_topology_integrity（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-37_graph_topology_integrity.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-37_graph_topology_integrity.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-37_graph_topology_integrity.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-37.graph_topology_integrity"

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
    "mechanism": "LIT-B-37",
    "mechanism_source": "B-37 · ACL 2026 Long · DOI 10.18653/v1/2026.acl-long.252 · 题名 \"LogicPoison: Logical Attacks on Graph Retrieval-Augmented Generation\"",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-37 Table 2（2Wiki 上跨不同 LLM 与 RAG 框架的攻击性能）",
        "B-37 Table 3（效率分析）",
        "B-37 Fig. 3（组件消融）",
        "B-37 Fig. 4（基于困惑度的检测 AUC）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-37",
        "locator": "B-37 (ACL 2026 Long, DOI 10.18653/v1/2026.acl-long.252) Table 2 与 Fig. 3：拓扑面攻击为独立构造，与三元组补链(B-28) 的内容面构造不同，各有独立实验",
        "value": "LIT-B-37"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-28.perturbation_triple_insertion"
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
