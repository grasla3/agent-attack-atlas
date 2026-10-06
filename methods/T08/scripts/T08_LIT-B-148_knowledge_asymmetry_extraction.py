#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识不对称细粒度抽取：查询分解最大化 RAG 与裸 LLM 的信息散度，再用语义关系打分消歧并迭代精炼

派生自 methods/T08/T08.py + 卡 T08.LIT-B-148.knowledge_asymmetry_extraction（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T08_LIT-B-148_knowledge_asymmetry_extraction.py --plan         # 打印执行计划（不执行）
  python T08_LIT-B-148_knowledge_asymmetry_extraction.py --plan --grid  # 按维度档位展开
  python T08_LIT-B-148_knowledge_asymmetry_extraction.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T08  # noqa: E402

METHOD_ID = 'T08.LIT-B-148.knowledge_asymmetry_extraction'

#: 参数：档位可变项（S3）
PARAMS = {'entry_point': '用户输入',
 'write_tool': 'user_turn',
 'artifact_kind': 'text_only',
 'budget_grid': [1, 3, 5],
 'placement_grid': ['task_context', 'tool_result', 'retrieval_doc'],
 'granularity': '单文档',
 'trigger': '查询触发',
 'turns': 10,
 'custom_logic_required': True,
 'distinctness_axis': 'mechanism_first_step'}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {'mechanism': 'LIT-B-148',
 'mechanism_source': 'B-148 · arXiv 2507.23229 · arXiv:2507.23229',
 'vector': '用户输入',
 'vector_source': 'docs/domain-and-literature.md §2（Kim 2026 §4.1 V1–V6）；B-148 §4.1 '
                  '攻击者仅提交对抗查询',
 'technique': '自动生成',
 'technique_source': 'docs/domain-and-literature.md §2.4（越狱六类方法学）——查询由算法按散度目标生成',
 'transform': None,
 'provenance_kind': 'interpolation',
 'source_grade': 'B',
 'numeric_evidence': 'original_table',
 'verifier': 'sensitive_data',
 'evidence_layer': 'behavior',
 'negative_control': 'T08.LIT-B-145.semantic_trigger_memory_exfiltration',
 'distinctness_evidence': {'axis': 'mechanism_first_step',
                           'ref': 'LIT-B-148',
                           'locator': 'B-148 §4「查询分解最大化信息散度 + 语义关系打分」；与 B-153 的自适应查询、B-145 的触发器不同',
                           'value': 'LIT-B-148'},
 'source_refs': ['B-148 Table 1（HCM | LLaMA3.1-8B | 93.55% | 92.06% | 89.40%）',
                 'B-148 Table 5（q1 52.94% vs q1⊕q2 80.00%）',
                 'B-148 Table 3（标准 LLM 对照）',
                 'B-148 Table 4（检索器消融）',
                 'B-148 Table 6（作者自研 CoT 防御下 PDR 48.27%）'],
 'custom_logic_reason': '查询分解须以 **RAG 与裸 LLM 的响应散度**为反馈逐轮精炼（Algorithm 1 迭代 10 轮），是运行期闭环'}


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
