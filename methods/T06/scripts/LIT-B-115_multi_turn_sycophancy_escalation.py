#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多轮谄媚升级：利用谄媚效应逐轮抬高提示泄露率

派生自 methods/T06/T06.py + 卡 T06.LIT-B-115.multi_turn_sycophancy_escalation（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-115_multi_turn_sycophancy_escalation.py --plan         # 打印执行计划（不执行）
  python LIT-B-115_multi_turn_sycophancy_escalation.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-115_multi_turn_sycophancy_escalation.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-115.multi_turn_sycophancy_escalation"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "用户输入",
    "entry_tool": "user_turn",
    "artifact_kind": "chat_log",
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
    "turns": 5,
    "dimensions": [
        "turns",
        "query_template"
    ],
    "side_channel": False,
    "custom_logic_required": False
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-115",
    "mechanism_source": "B-115（arXiv 2404.16251，无 venue）Table 2（不同场景平均 ASR）/ Table 4（泄露类型分布）/ Table 5、6、10（各防御下的 ASR 变化）/ Table 7（查询与 top-2 知识统计）：ASR 17.7% -> 86.2%",
    "vector": "用户输入",
    "technique": "多轮分阶段",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-115（arXiv 2404.16251，无 venue）Table 2（不同场景平均 ASR）/ Table 4（泄露类型分布）/ Table 5、6、10（各防御下的 ASR 变化）/ Table 7（查询与 top-2 知识统计）：ASR 17.7% -> 86.2%",
        "results/README.md #11",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-115",
        "locator": "B-115（arXiv 2404.16251）Table 2/5：多轮 ASR 17.7%->86.2%，并有逐防御对照",
        "value": "谄媚驱动的轮次级升级（dialogue_shape=crescendo）"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-116.output_inversion_prompt_recovery",
    "bib_id": "B-115（ar"
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
