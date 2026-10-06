#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""缓存共享统计审计：以假设检验判定跨用户/全局提示缓存共享

派生自 methods/T06/T06.py + 卡 T06.LIT-B-118.statistical_cache_audit（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python LIT-B-118_statistical_cache_audit.py --plan         # 打印执行计划（不执行）
  python LIT-B-118_statistical_cache_audit.py --plan --grid  # 按维度档位展开参数网格
  python LIT-B-118_statistical_cache_audit.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "T06.LIT-B-118.statistical_cache_audit"

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
    "mechanism": "LIT-B-118",
    "mechanism_source": "B-118 Auditing Prompt Caching（ICML 2025）3.1 节（审计形式化）/ Table 1（检出缓存的 API）/ Table 2（未检出）/ Figure 3（命中/未命中响应时间直方图）/ Figure 4（精确率-召回率曲线）：17 家中 8 家检出、其中 7 家全局共享",
    "vector": "系统提示词",
    "technique": "模型缺陷",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "S",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-118 Auditing Prompt Caching（ICML 2025）3.1 节（审计形式化）/ Table 1（检出缓存的 API）/ Table 2（未检出）/ Figure 3（命中/未命中响应时间直方图）/ Figure 4（精确率-召回率曲线）：17 家中 8 家检出、其中 7 家全局共享",
        "results/README.md #14",
        "docs/domain-and-literature.md（本类文献表，收录方 T06）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-118",
        "locator": "B-118（ICML 2025）Table 1 与 Figure 4：8/17 家检出缓存、7 家全局共享，含 PR 曲线",
        "value": "把缓存共享检测形式化为统计假设检验（审计式，非恢复式）"
    },
    "verifier": "prompt_leak",
    "evidence_layer": "text",
    "negative_control": "T06.LIT-B-120.hard_token_dpo_reconstruction",
    "bib_id": "B-118 Au"
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
