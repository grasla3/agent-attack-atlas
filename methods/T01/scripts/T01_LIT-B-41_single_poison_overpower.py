#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单条毒文本压制投毒：在现实注入预算下，用一条毒文本压过全部正确文本

派生自 methods/T01/T01.py + 卡 T01.LIT-B-41.single_poison_overpower（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T01_LIT-B-41_single_poison_overpower.py --plan         # 打印执行计划（不执行）
  python T01_LIT-B-41_single_poison_overpower.py --plan --grid  # 按维度档位展开
  python T01_LIT-B-41_single_poison_overpower.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "T01.LIT-B-41.single_poison_overpower"

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
    "mechanism": "LIT-B-41",
    "mechanism_source": "B-41 · ACM SACMAT 2026 · DOI 10.1145/3750555.3811900 · 题名 \"Practical Poisoning Attacks against Retrieval-Augmented Generation\" · 方法名 CorruptRAG",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "A",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-41 Table 2（三个数据集上的攻击结果）",
        "B-41 Table 3（PoisonedRAG 在 NQ 上需注入多条时的对比）",
        "B-41 Table 4（每条查询的投毒成本，USD）",
        "B-41 Table 5–9（不同检索器 / 相似度度量 / 拼接顺序与变体）",
        "B-41 正文：NQ 81% / HotpotQA 80% / MS-MARCO 84%"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-41",
        "locator": "B-41 (SACMAT 2026, DOI 10.1145/3750555.3811900) Table 2/3/4：单条压制构造（含成本）为独立构造，与多文档灌入式构造不同，各有独立实验",
        "value": "LIT-B-41"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T01.LIT-B-40.embedding_space_optimization"
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
