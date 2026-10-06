#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检索器引导的词级精炼投毒：以检索器反馈逐词优化对抗文档，使其被稳定召回

派生自 methods/T01/T01.py + 卡 T01.LIT-B-44.retriever_guided_word_refinement（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-44_retriever_guided_word_refinement.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-44_retriever_guided_word_refinement.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-44_retriever_guided_word_refinement.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-44.retriever_guided_word_refinement"

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
    "custom_logic_required": True,
    "distinctness_axis": "mechanism_first_step"
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-44",
    "mechanism_source": "B-44 · LNCS / Pattern Recognition 2026（会议录，非 SCI 期刊）· DOI 10.1007/978-3-032-31583-0_35 · 题名 \"RefineRAG: Word-Level Poisoning Attacks via Retriever-Guided Text Refinement\" · arXiv:2604.07403",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-44 Table 1（与基线方法对比：有效性/隐蔽性权衡）",
        "B-44 Table 2（跨 6 个开源 LLM 的迁移性）",
        "B-44 Table 3（跨检索器迁移性）",
        "B-44 Figure 2（检索范围 k 的影响，NQ）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-44",
        "locator": "B-44 (LNCS/Pattern Recognition 2026, DOI 10.1007/978-3-032-31583-0_35) Table 1/2/3：词级精炼为独立构造，与\"挑选现成样例\"(B-25)、\"片段分解\"(B-26) 为不同构造，各有独立实验",
        "value": "LIT-B-44"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-25.select_existing_vulnerable_sample"
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
