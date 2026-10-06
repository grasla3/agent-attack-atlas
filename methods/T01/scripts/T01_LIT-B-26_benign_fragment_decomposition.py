#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""片段分解式隐蔽投毒：把漏洞代码拆成良性外观片段注入知识库，由 LLM 在检索后自行补全为漏洞代码

派生自 methods/T01/T01.py + 卡 T01.LIT-B-26.benign_fragment_decomposition（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-26_benign_fragment_decomposition.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-26_benign_fragment_decomposition.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-26_benign_fragment_decomposition.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-26.benign_fragment_decomposition"

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
    "custom_logic_required": True,
    "distinctness_axis": "mechanism_first_step"
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-26",
    "mechanism_source": "B-26, IEEE TDSC 2026, Vol 23 No 4 pp.8649-8666, \"Covert Knowledge Poisoning Attacks in Retrieval-Augmented Code Generation\"（方法名 Arachne），两机制： Benign-Appearing Fragment Construction + Retrieval-Driven Knowledge Completion",
    "vector": "检索文档",
    "technique": "手工设计",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "composition",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-26 Table I（Arachne 在各设置下的有效性）",
        "B-26 Table II（跨 MITRE Top-25 软件弱点的 ASR）",
        "B-26 Table III（与基线对比，含 ASR 与 F1）",
        "B-26 正文：多数设置下 ASR > 70%；相对既有投毒攻击最高提升 37%"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-26",
        "locator": "B-26 (IEEE TDSC 2026, Vol 23 No 4, pp.8649-8666) Table I 与 Table II：Arachne 在片段分解设定下的 ASR，与\"注入现成漏洞样例\"（B-25 Scenario I）为两次独立构造，各有独立实验",
        "value": "LIT-B-26"
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
