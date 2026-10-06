#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step-Wave 边界碰撞：非前缀 KV 缓存融合中的长度指纹与逐 token 提取

派生自 methods/T06/T06.py + 卡 T06.LIT-B-122.stepwave_boundary_collision（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-122_stepwave_boundary_collision.py --plan         # 打印执行计划（不执行）
  python LIT-B-122_stepwave_boundary_collision.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-122_stepwave_boundary_collision.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-122.stepwave_boundary_collision"

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
    "custom_logic_required": True
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-122",
    "mechanism_source": "B-122 SpliceLeak（arXiv 2606.21842，无 venue）Fig. 1（缓存共享机制对比）/ Fig. 2（微架构时间线）/ Fig. 5、6（TTFT 侧信道与剖析）/ Fig. 7（场景 A）：结构化场景最高 100% 提取成功、63 请求/token",
    "vector": "系统提示词",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-122 SpliceLeak（arXiv 2606.21842，无 venue）Fig. 1（缓存共享机制对比）/ Fig. 2（微架构时间线）/ Fig. 5、6（TTFT 侧信道与剖析）/ Fig. 7（场景 A）：结构化场景最高 100% 提取成功、63 请求/token",
        "results/README.md #17",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-122",
        "locator": "B-122（arXiv 2606.21842）Fig. 5/7：最高 100% 提取、63 请求/token，含场景 A/B 对照",
        "value": "非前缀（chunk 融合）缓存的边界碰撞操纵"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-123.schema_completion_parameter_exfil",
    "bib_id": "B-122 Sp"
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
