#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指令遵循式数据存储重建：以「复制该句之前的全部文本」类注入让 RIC-RAG 逐条回吐语料，对生产 GPTs 改用文件浏览函数调用

派生自 methods/T08/T08.py + 卡 T08.LIT-B-158.instruction_following_datastore_extraction（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T08_LIT-B-158_instruction_following_datastore_extraction.py --plan         # 打印执行计划（不执行）
  python T08_LIT-B-158_instruction_following_datastore_extraction.py --plan --grid  # 按维度档位展开
  python T08_LIT-B-158_instruction_following_datastore_extraction.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T08  # noqa: E402

METHOD_ID = 'T08.LIT-B-158.instruction_following_datastore_extraction'

#: 参数：档位可变项（S3）
PARAMS = {'entry_point': '用户输入',
 'write_tool': 'user_turn',
 'artifact_kind': 'text_only',
 'budget_grid': [1, 3, 5],
 'placement_grid': ['task_context', 'tool_result', 'retrieval_doc'],
 'granularity': '单文档',
 'trigger': '查询触发',
 'turns': 64,
 'custom_logic_required': False,
 'distinctness_axis': 'mechanism_first_step'}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {'mechanism': 'LIT-B-158',
 'mechanism_source': 'B-158 · ICLR 2025 · openreview/ICLR-2025',
 'vector': '用户输入',
 'vector_source': 'docs/domain-and-literature.md §2（Kim 2026 §4.1 V1–V6）；B-158 Fig. 1 '
                  'caption：注入位于用户输入',
 'technique': '手工设计',
 'technique_source': 'docs/domain-and-literature.md §2.4（越狱六类方法学，域地图行 16）',
 'transform': None,
 'provenance_kind': 'interpolation',
 'source_grade': 'S',
 'numeric_evidence': 'original_table',
 'verifier': 'prompt_leak',
 'evidence_layer': 'behavior',
 'negative_control': 'T08.LIT-B-148.knowledge_asymmetry_extraction',
 'distinctness_evidence': {'axis': 'mechanism_first_step',
                           'ref': 'LIT-B-158',
                           'locator': 'B-158 Definition 1：机制首步是**利用指令遵循让模型复述检索上下文**，再对生产 GPTs '
                                      '换成文件浏览函数调用；与 B-148 的散度判别、B-153 的查询规划不同',
                           'value': 'LIT-B-158'},
 'source_refs': ['B-158 Table 1（10 模型；Qwen1.5-Chat-72b ROUGE-L 99.154±0.348）',
                 'B-158 Table 2（Harry Potter +5.743）',
                 'B-158 Table 3（缓解：PINE 重建率 88.88→58.03）',
                 'B-158 Fig. 6（100 查询抽 41.73% 书 / 3.22% 语料）',
                 'B-158 §4 正文：25 个 GPTs 上 100% 成功率（**prose-only，无表无图**）']}


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
