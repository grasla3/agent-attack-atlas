#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出反演：仅用正常查询的输出训练反演模型恢复提示（无 logits、无对抗查询）

派生自 methods/T06/T06.py + 卡 T06.LIT-B-116.output_inversion_prompt_recovery（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-116_output_inversion_prompt_recovery.py --plan         # 打印执行计划（不执行）
  python LIT-B-116_output_inversion_prompt_recovery.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-116_output_inversion_prompt_recovery.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-116.output_inversion_prompt_recovery"

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
    "turns": 1,
    "dimensions": [
        "query_template",
        "probe_budget",
        "artifact_form"
    ],
    "side_channel": False,
    "custom_logic_required": False
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-116",
    "mechanism_source": "B-116 output2prompt（EMNLP 2024）Table 1（Instructions-2M 主结果）/ Table 2（跨 LLM 迁移）/ Table 3（跨数据集）/ Table 4 / Figure 1（流水线）",
    "vector": "用户输入",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-116 output2prompt（EMNLP 2024）Table 1（Instructions-2M 主结果）/ Table 2（跨 LLM 迁移）/ Table 3（跨数据集）/ Table 4 / Figure 1（流水线）",
        "results/README.md #12",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-116",
        "locator": "B-116（EMNLP 2024）Table 1/2/3：主结果 + 跨模型零样本迁移均有对照",
        "value": "输入/输出反转（稀疏编码聚合），不使用对抗查询"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-117B.latent_trait_inference",
    "bib_id": "B-116 ou"
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
