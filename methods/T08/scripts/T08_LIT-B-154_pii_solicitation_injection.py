#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主动索要式注入：注入含假记忆的数据，使应用反过来成批向用户索要 PII（而非从输出侧泄露）

派生自 methods/T08/T08.py + 卡 T08.LIT-B-154.pii_solicitation_injection（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T08_LIT-B-154_pii_solicitation_injection.py --plan         # 打印执行计划（不执行）
  python T08_LIT-B-154_pii_solicitation_injection.py --plan --grid  # 按维度档位展开
  python T08_LIT-B-154_pii_solicitation_injection.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T08  # noqa: E402

METHOD_ID = 'T08.LIT-B-154.pii_solicitation_injection'

#: 参数：档位可变项（S3）
PARAMS = {'entry_point': '检索文档',
 'write_tool': 'kb_write',
 'artifact_kind': 'text_only',
 'budget_grid': [1, 3, 5],
 'placement_grid': ['task_context', 'tool_result', 'retrieval_doc'],
 'granularity': '单文档',
 'trigger': '常驻',
 'turns': 1,
 'custom_logic_required': False,
 'distinctness_axis': 'mechanism_first_step'}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {'mechanism': 'LIT-B-154',
 'mechanism_source': 'B-154 · Findings of the EACL 2026 pp.587-609 · '
                     '10.18653/v1/2026.findings-eacl.29',
 'vector': '检索文档',
 'vector_source': 'docs/domain-and-literature.md §2（旧 T02 降级）；B-154 Algorithm 1 第 1–2 行：把 '
                  'f(PS) 并入外部数据 ED',
 'technique': '手工设计',
 'technique_source': 'docs/domain-and-literature.md §2.4（越狱六类方法学，域地图行 16）',
 'transform': '外壳模板',
 'provenance_kind': 'interpolation',
 'source_grade': 'A',
 'numeric_evidence': 'original_table',
 'verifier': 'sensitive_data',
 'evidence_layer': 'behavior',
 'negative_control': 'T08.LIT-B-148.knowledge_asymmetry_extraction',
 'distinctness_evidence': {'axis': 'mechanism_first_step',
                           'ref': 'LIT-B-154',
                           'locator': 'B-154 §3.2：机制首步是**让模型把 PII '
                                      '当作已知事实并主动向用户复述索要**；与所有「从输出/工具侧取数」的方法方向相反',
                           'value': 'LIT-B-154'},
 'source_refs': ['B-154 Table 1（ASR：VORTEX PIA 65.75/97.75/86.50/94.50 vs CAI '
                 '33.75/89.20/59.50/81.00）',
                 'B-154 Table 2（PR 44.88 vs 常规 PIA 99.39，检测下暴露度更低）',
                 'B-154 正文 Qwen2.5-72B 90.9%']}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T08.spec_from_card(METHOD_ID)
    spec.injection.budget_grid = PARAMS["budget_grid"]
    spec.injection.placement_grid = PARAMS["placement_grid"]

    if "--params" in argv:
        print(json.dumps({"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        plans = T08.plan_grid(spec) if "--grid" in argv else [T08.build_plan(spec)]
        print(json.dumps(plans if "--grid" in argv else plans[0],
                         ensure_ascii=False, indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
