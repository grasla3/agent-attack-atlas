#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词级后门触发器投毒：把触发词嵌入语料文档，命中即输出攻击者指定答案

派生自 methods/T01/T01.py + 卡 T01.LIT-B-32.word_level_trigger（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-32_word_level_trigger.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-32_word_level_trigger.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-32_word_level_trigger.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-32.word_level_trigger"

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
    "trigger": "休眠触发",
    "turns": 1,
    "custom_logic_required": True,
    "distinctness_axis": "mechanism_first_step"
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-32",
    "mechanism_source": "B-32 · ACM KDD 2026 V.1 · pp.867-878 · DOI 10.1145/3770854.3780227 · 题名 \"WARP: A Word-Level Backdoor Attack Targeting RAG Systems via Retrieval Corpus Poisoning\"",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-32 Table 1（2 检索器 x 3 数据集 x 5 种触发词配置；平均 ASR 55.8%，较既有方法 +17.2%，良性查询退化 <0.1%）",
        "B-32 Table 2（MS-MARCO 上与两基线对比）· Table 10/11（HotpotQA / NQ）",
        "B-32 Table 3（困惑度对比；平均 PPL 69.98，较 SOTA 降 95.6%）",
        "B-32 Table 4–7（消融：L_coh / top-m / 困惑度正则）· Table 12（RobustRAG 防御下 ASR）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-32",
        "locator": "B-32 (KDD 2026 V.1, pp.867-878) Table 1 与 Table 4：词级触发器为独立构造，与束搜索优化(B-31) 的构造不同，各有独立实验",
        "value": "LIT-B-32"
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
