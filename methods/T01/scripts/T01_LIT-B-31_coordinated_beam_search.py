#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协调束搜索投毒：以流畅度-相似度联合目标生成可召回文档，再融合自适应触发器

派生自 methods/T01/T01.py + 卡 T01.LIT-B-31.coordinated_beam_search（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-31_coordinated_beam_search.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-31_coordinated_beam_search.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-31_coordinated_beam_search.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-31.coordinated_beam_search"

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
    "mechanism": "LIT-B-31",
    "mechanism_source": "B-31 · ACM KDD 2026 V.2 · pp.4012-4023 · DOI 10.1145/3770855.3818186 · arXiv:2605.28074 · 题名 \"SilentRetrieval: Hijacking Retrieval-Augmented Generation via Semantically-Preserving Adversarial Data Poisoning\" · 两阶段：Coordinated Beam Search + Context-Adaptive Trigger Generation",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-31 Table 1（NQ：361K 语料 / 3,452 查询的主结果，bootstrap 95% CI，1000 次重采样）",
        "B-31 Table 2（跨模型评估，ASR-LLM 48.6–57.5%）",
        "B-31 Table 3（代理迁移攻击）",
        "B-31 Table 4/5（检索侧 / 生成侧防御评估）",
        "B-31 Table 6/7（自适应攻击；人工评估 n=600 文档）",
        "B-31 Table 8（可扩展性）· Table 10/11（附录：14 方法对比）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-31",
        "locator": "B-31 (KDD 2026 V.2, pp.4012-4023) Table 1 与 Table 4：协调束搜索 + 触发融合为独立构造，与词级精炼(B-44)、片段分解(B-26) 的构造不同，各有独立实验",
        "value": "LIT-B-31"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-44.retriever_guided_word_refinement"
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
