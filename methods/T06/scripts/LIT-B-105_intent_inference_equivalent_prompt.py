#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""意图推断式提示窃取：以有限输入-输出对推断提示意图并生成等价窃取提示

派生自 methods/T06/T06.py + 卡 T06.LIT-B-105.intent_inference_equivalent_prompt（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-105_intent_inference_equivalent_prompt.py --plan         # 打印执行计划（不执行）
  python LIT-B-105_intent_inference_equivalent_prompt.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-105_intent_inference_equivalent_prompt.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-105.intent_inference_equivalent_prompt"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "用户输入",
    "entry_tool": "user_turn",
    "artifact_kind": "task_context",
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
    "mechanism": "LIT-B-105",
    "mechanism_source": "B-105 PRSA（USENIX Security 2025）Table 2（GPT-3.5 提示窃取性能）/ Table 3（相似度）/ Table 4（LLM 多维评价）/ Table 5、7（对比 ASR）/ Figure 6（100 个 GPT 的分布）：ASR 17.8%->46.1%（prompt marketplaces）、39%->52%（LLM app stores）",
    "vector": "用户输入",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-105 PRSA（USENIX Security 2025）Table 2（GPT-3.5 提示窃取性能）/ Table 3（相似度）/ Table 4（LLM 多维评价）/ Table 5、7（对比 ASR）/ Figure 6（100 个 GPT 的分布）：ASR 17.8%->46.1%（prompt marketplaces）、39%->52%（LLM app stores）",
        "results/README.md #1（表号级举证）",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-105",
        "locator": "B-105 PRSA（USENIX Security 2025）Table 2/5 与 Figure 6：ASR 46.1%（marketplace）与 52%（app store），有独立对照设计",
        "value": "用户输入->意图推断->等价重构"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-106.gradient_optimized_adversarial_query",
    "bib_id": "B-105 PR"
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
