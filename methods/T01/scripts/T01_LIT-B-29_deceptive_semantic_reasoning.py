#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""欺骗性语义推理记忆投毒：用语义推理链而非触发词欺骗 RAG agent 的记忆更新

派生自 methods/T01/T01.py + 卡 T01.LIT-B-29.deceptive_semantic_reasoning（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-29_deceptive_semantic_reasoning.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-29_deceptive_semantic_reasoning.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-29_deceptive_semantic_reasoning.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-29.deceptive_semantic_reasoning"

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
    "mechanism": "LIT-B-29",
    "mechanism_source": "B-29 · Engineering Applications of Artificial Intelligence 2026 · Vol 167 ArtNo 113968 · DOI 10.1016/j.engappai.2026.113968 · 题名 \"Memory poisoning attacks on retrieval-augmented Large Language Model agents via deceptive semantic reasoning\" · 方法名 DSRM",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-29 Table 2（与三基线对比；ASR_A / ASR_R 两指标；ASR_A 41.0% vs PoisonedRAG 34.0%）",
        "B-29 Table 3（白盒设定下的对比）",
        "B-29 Table 5（记忆更新对攻击持续性的影响；ASR 随更新递减）",
        "B-29 Table 9（不同模块的消融）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-29",
        "locator": "B-29 (EAAI 2026, Vol 167, ArtNo 113968) Table 2 与 Table 5：语义推理链构造 + 记忆持久性为独立构造，与检索侧投毒不同，各有独立实验",
        "value": "LIT-B-29"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-41.single_poison_overpower"
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
