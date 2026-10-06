#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两步式数据窃取臂：工具返回里植入指令，先用取数工具读出用户私密数据，再用发信工具把它发给攻击者（读+发两跳都须成功）

派生自 methods/T08/T08.py + 卡 T08.B-T08-07.two_step_data_stealing_arm（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T08_B-T08-07_two_step_data_stealing_arm.py --plan         # 打印执行计划（不执行）
  python T08_B-T08-07_two_step_data_stealing_arm.py --plan --grid  # 按维度档位展开
  python T08_B-T08-07_two_step_data_stealing_arm.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T08  # noqa: E402

METHOD_ID = 'T08.B-T08-07.two_step_data_stealing_arm'

#: 参数：档位可变项（S3）
PARAMS = {'entry_point': '工具返回',
 'write_tool': 'tool_return',
 'artifact_kind': 'tool_return',
 'budget_grid': [1, 3, 5],
 'placement_grid': ['task_context', 'tool_result', 'retrieval_doc'],
 'granularity': '单文档',
 'trigger': '常驻',
 'turns': 1,
 'custom_logic_required': False,
 'distinctness_axis': 'mechanism_first_step'}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {'mechanism': 'LIT-B-159',
 'mechanism_source': 'B-159（= 共享池 B-07）· Findings of the ACL 2024, pp.10471-10506 · DOI '
                     '10.18653/v1/2024.findings-acl.624 · 「InjecAgent: Benchmarking Indirect '
                     'Prompt Injections in Tool-Integrated Large Language Model Agents」（data '
                     'stealing 臂）',
 'vector': '工具返回',
 'vector_source': 'docs/domain-and-literature.md §2（旧 T02 降级：工具返回注入）；B-159 '
                  '§2.2：在用户工具返回模板的**攻击者可改字段**（如 content）里替换占位符',
 'technique': '自动生成',
 'technique_source': 'docs/domain-and-literature.md §2.4（越狱六类方法学，域地图行 16）——测试用例由 GPT-4 生成器合成',
 'transform': '外壳模板',
 'provenance_kind': 'interpolation',
 'source_grade': 'A',
 'numeric_evidence': 'original_table',
 'verifier': 'sensitive_data',
 'evidence_layer': 'behavior',
 'negative_control': 'T08.LIT-B-149.dataflow_injection_personal_data',
 'distinctness_evidence': {'axis': 'mechanism_first_step',
                           'ref': 'LIT-B-159',
                           'locator': 'B-159 §2.1–§2.2：本卡取该文的 **data stealing 臂**（另一个臂 direct harm '
                                      '的终点是"用工具直接损害用户"—— 转账、开门等状态改变，属 **T04**，本卡不收，见 '
                                      'secondary_assets 与 docs/method-capacity-audit.md 的跨类表）。 '
                                      '机制首步是**在用户工具返回的可改字段里替换占位符**，植入"先取数、再发信"的**两跳**指令； '
                                      '原文为该臂单独定义（§2.1 两类攻击并列陈述）、单独建 544 个用例、并在 Table 3/4/9 '
                                      '中**单独成列**报数 ⇒ 与 direct harm 臂是**两种独立构造**，不是同一实验的两种配置（按 '
                                      'ruling-c4-vs-c11 §三，C11 优先，允许拆臂）。 与 T08 '
                                      '其余方法亦不同：其余多为单跳外泄（一次工具调用即带出数据），本卡要求**取数与外发两跳均成功**。',
                           'value': 'LIT-B-159'},
 'source_refs': ['B-159 Table 2（17 个 user case × 62 个 attacker case = 1,054 个测试用例；其中 Direct harm '
                 '30 / Data stealing 32）',
                 'B-159 Table 3（base 与 enhanced 两档按模型分列，Direct Harm 与 Data Stealing 分开报：GPT-4 '
                 '`14.7 32.7 97.7 31.9 23.6 | 33.3 61.0 98.2 59.9 47.0`）',
                 'B-159 Table 4（两类攻击的对比：Direct Harm `AC. 0.18 / UC. 0.28 / p=5×10−5`；Data Stealing '
                 '`AC. 0.20 / UC. 0.31 / p=0.0001`）',
                 'B-159 Table 7/8/9（ASR-valid 与 ASR-all 两口径；Table 9 按攻击类型分列）',
                 'B-159 Table 11/12（长 ReAct 提示 vs 短 Langchain 提示的鲁棒性对比）与微调档（GPT-3.5/GPT-4 '
                 'fine-tuned 的 Total 3.8 / 6.6）']}


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
