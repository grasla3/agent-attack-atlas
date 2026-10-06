#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语义缓存侧信道（Peeping Neighbor）：跨租户语义相似命中的提示泄露

派生自 methods/T06/T06.py + 卡 T06.LIT-B-113B.semantic_cache_side_channel（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-113B_semantic_cache_side_channel.py --plan         # 打印执行计划（不执行）
  python LIT-B-113B_semantic_cache_side_channel.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-113B_semantic_cache_side_channel.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-113B.semantic_cache_side_channel"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "系统提示词",
    "entry_tool": "cache_probe",
    "artifact_kind": "config_fragment",
    "budget_grid": [
        1,
        10,
        50
    ],
    "turns_grid": [
        1,
        3,
        5
    ],
    "turns": 1,
    "dimensions": [
        "extraction_channel",
        "probe_budget"
    ],
    "side_channel": True,
    "custom_logic_required": False
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-113B",
    "mechanism_source": "B-113 Early Bird（IEEE TIFS 2025）Fig. 7（Peeping Neighbor Attacks）/ Fig. 8、9（语义泄露与 ROC：语义缓存共享的泄露画像）",
    "vector": "系统提示词",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-113 Early Bird（IEEE TIFS 2025）Fig. 7（Peeping Neighbor Attacks）/ Fig. 8、9（语义泄露与 ROC：语义缓存共享的泄露画像）",
        "results/README.md #9（文内第二档）",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-113B",
        "locator": "B-113（IEEE TIFS 2025）Fig. 7/9：语义缓存侧信道为同文内独立机制，含 ROC 级量化",
        "value": "语义缓存（非前缀匹配）侧信道"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-113.kv_cache_timing_prefix_recovery",
    "bib_id": "B-113 Ea"
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T06.spec_from_card(METHOD_ID)
    spec.probe.budget = PARAMS["budget_grid"][0]
    spec.turns_grid = PARAMS["turns_grid"]

    if "--params" in argv:
        print(json.dumps({"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        print(json.dumps(T06.plan_grid(spec) if "--grid" in argv else T06.build_plan(spec),
                         ensure_ascii=False, indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
