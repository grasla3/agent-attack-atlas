#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文档对抗思维链投毒：先抽取目标模型推理框架，再迭代精炼一篇对抗文档

派生自 methods/T01/T01.py + 卡 T01.LIT-B-39.single_doc_adversarial_cot（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-39_single_doc_adversarial_cot.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-39_single_doc_adversarial_cot.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-39_single_doc_adversarial_cot.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-39.single_doc_adversarial_cot"

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
    "mechanism": "LIT-B-39",
    "mechanism_source": "B-39 · ACM SIGIR 2026 · DOI 10.1145/3805712.3809838 · 题名 \"AdversarialCoT: Single-Document Retrieval Poisoning for LLM Reasoning\"",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-39 Table 1（推理三阶段示例说明）",
        "B-39 Table 2（在先进模型上的攻击有效性）",
        "B-39 Table 3（ASRr / ASRg / ASR 三指标跨方法对比）",
        "B-39 正文：攻击成功率较既有投毒方法最高提升 23%；迭代式优于非迭代式"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-39",
        "locator": "B-39 (SIGIR 2026, DOI 10.1145/3805712.3809838) Table 2/3：推理框架抽取 + 单文档 CoT 构造为独立构造，与词级触发器(B-32)、束搜索(B-31) 不同，各有独立实验",
        "value": "LIT-B-39"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-31.coordinated_beam_search"
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
