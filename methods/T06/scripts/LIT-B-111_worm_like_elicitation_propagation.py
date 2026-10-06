#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蠕虫式多智能体外带：elicitation->propagation->retention 三阶段提取系统提示与拓扑

派生自 methods/T06/T06.py + 卡 T06.LIT-B-111.worm_like_elicitation_propagation（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-111_worm_like_elicitation_propagation.py --plan         # 打印执行计划（不执行）
  python LIT-B-111_worm_like_elicitation_propagation.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-111_worm_like_elicitation_propagation.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-111.worm_like_elicitation_propagation"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "智能体间消息",
    "entry_tool": "agent_message",
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
    "turns": 3,
    "dimensions": [
        "query_template",
        "turns",
        "artifact_form"
    ],
    "side_channel": False,
    "custom_logic_required": False
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-111",
    "mechanism_source": "B-111 MASLeak（USENIX Security 2026）Fig. 3（两阶段流水线）/ TABLE 1（主结果）/ TABLE 2（仅成功提取）/ TABLE 3（对基线）/ TABLE 4、5（提示技巧与 qLeak 生成法）：ASR 87%（提示/任务指令）、92%（架构）",
    "vector": "智能体间消息",
    "technique": "多轮分阶段",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-111 MASLeak（USENIX Security 2026）Fig. 3（两阶段流水线）/ TABLE 1（主结果）/ TABLE 2（仅成功提取）/ TABLE 3（对基线）/ TABLE 4、5（提示技巧与 qLeak 生成法）：ASR 87%（提示/任务指令）、92%（架构）",
        "results/README.md #7",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-111",
        "locator": "B-111 MASLeak（USENIX Security 2026）TABLE 1/3：ASR 87% 与 92%，跨 810 个合成与真实 MAS 应用",
        "value": "多智能体传播链（elicitation->propagation->retention）"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-112.ucb_skill_evolution_probing",
    "bib_id": "B-111 MA"
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
