#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两阶段 harness 蒸馏：黑盒推断推理期 harness 行为并迭代精炼克隆体

派生自 methods/T06/T06.py + 卡 T06.LIT-B-124.two_stage_harness_distillation（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-124_two_stage_harness_distillation.py --plan         # 打印执行计划（不执行）
  python LIT-B-124_two_stage_harness_distillation.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-124_two_stage_harness_distillation.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-124.two_stage_harness_distillation"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "用户输入",
    "entry_tool": "user_turn",
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
    "turns": 3,
    "dimensions": [
        "query_template",
        "probe_budget",
        "turns"
    ],
    "side_channel": False,
    "custom_logic_required": True
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-124",
    "mechanism_source": "B-124 AHD（arXiv 2607.28147，无 venue）Table 1（IP 泄露消融）/ Table 2（跨模型泛化）/ Table 3（防御有效性）/ Table 4（harness 相似度）/ Figure 1：53.3% 准确率、较 pre-distilled 提升 23.1%",
    "vector": "用户输入",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-124 AHD（arXiv 2607.28147，无 venue）Table 1（IP 泄露消融）/ Table 2（跨模型泛化）/ Table 3（防御有效性）/ Table 4（harness 相似度）/ Figure 1：53.3% 准确率、较 pre-distilled 提升 23.1%",
        "results/README.md #19",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-124",
        "locator": "B-124（arXiv 2607.28147）Table 2/4：跨模型泛化与 harness 相似度，提升 23.1%",
        "value": "两阶段蒸馏（pre/post-distillation），克隆而非读出文本"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-105.intent_inference_equivalent_prompt",
    "bib_id": "B-124 AH"
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
