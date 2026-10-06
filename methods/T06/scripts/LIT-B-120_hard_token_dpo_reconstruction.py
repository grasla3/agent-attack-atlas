#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""硬 token 偏好优化重建：识别领域 hard token 并用 DPO 偏好对重建受害者提示

派生自 methods/T06/T06.py + 卡 T06.LIT-B-120.hard_token_dpo_reconstruction（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-120_hard_token_dpo_reconstruction.py --plan         # 打印执行计划（不执行）
  python LIT-B-120_hard_token_dpo_reconstruction.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-120_hard_token_dpo_reconstruction.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-120.hard_token_dpo_reconstruction"

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
    "mechanism": "LIT-B-120",
    "mechanism_source": "B-120 OptiLeak（arXiv 2602.20595，无 venue）Figure 2（流水线）/ Table 1（MedQA/FinanceBench/PubMedQA 主结果）/ Figure 3（SFT/DPO 消融）/ Table 2：ARPT 41.99 -> 30.27，摘要级每 token 请求数最多降 12.48x",
    "vector": "系统提示词",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-120 OptiLeak（arXiv 2602.20595，无 venue）Figure 2（流水线）/ Table 1（MedQA/FinanceBench/PubMedQA 主结果）/ Figure 3（SFT/DPO 消融）/ Table 2：ARPT 41.99 -> 30.27，摘要级每 token 请求数最多降 12.48x",
        "results/README.md #15",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-120",
        "locator": "B-120（arXiv 2602.20595）Table 1/2 与 Figure 3：ARPT 41.99->30.27，含 SFT/DPO 消融对照",
        "value": "hard-token 识别 + DPO 偏好优化"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-121.adaptive_input_time_feedback",
    "bib_id": "B-120 Op"
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
