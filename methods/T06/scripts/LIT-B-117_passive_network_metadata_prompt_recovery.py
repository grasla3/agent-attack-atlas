#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""被动网络元数据提示恢复：仅用访问 IP 与时序两阶段流水线恢复提示

派生自 methods/T06/T06.py + 卡 T06.LIT-B-117.passive_network_metadata_prompt_recovery（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-117_passive_network_metadata_prompt_recovery.py --plan         # 打印执行计划（不执行）
  python LIT-B-117_passive_network_metadata_prompt_recovery.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-117_passive_network_metadata_prompt_recovery.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-117.passive_network_metadata_prompt_recovery"

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
    "side_channel": False,
    "custom_logic_required": True
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-117",
    "mechanism_source": "B-117（arXiv 2508.20282，无 venue）Figure 1、3（攻击概览与两阶段流水线）/ Table 1（轨迹数据集）/ Table 2（5-shot ICL vs 微调）/ Table 3、4、5（提示恢复）：恢复 >73% 功能与领域知识",
    "vector": "系统提示词",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-117（arXiv 2508.20282，无 venue）Figure 1、3（攻击概览与两阶段流水线）/ Table 1（轨迹数据集）/ Table 2（5-shot ICL vs 微调）/ Table 3、4、5（提示恢复）：恢复 >73% 功能与领域知识",
        "results/README.md #13",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-117",
        "locator": "B-117（arXiv 2508.20282）Table 3/4/5：提示恢复 >73%，含部分可观测与噪声条件",
        "value": "被动网络观测（IP + 时序），不与被攻击系统交互"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-118.statistical_cache_audit",
    "bib_id": "B-117（ar"
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
