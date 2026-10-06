#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP 工具服务器多向量攻击族：多模态注入、puppet 与工具投毒的组合投递

派生自 methods/T03/T03.py + 卡 T03.B-58.mcp_multivector_pitfall（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T03_B-58_mcp_multivector_pitfall.py --plan         # 打印执行计划（不执行）
  python T03_B-58_mcp_multivector_pitfall.py --plan --grid  # 按维度档位展开
  python T03_B-58_mcp_multivector_pitfall.py --params       # 打印参数与引用块
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Windows 控制台默认 GBK，卡上文本含 ⇒ 等非 GBK 字符时 json.dumps 会 UnicodeEncodeError。
# T01 的生成器带这一行，本模块此前漏了 —— 实测 B-54/B-55 两张卡因此崩溃。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T03  # noqa: E402

METHOD_ID = "T03.B-58.mcp_multivector_pitfall"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "工具返回",
    "entry_tool": "tool_result",
    "artifact_kind": "tool_return",
    "privilege_surface_grid": [
        "工具调用",
        "浏览器状态",
        "人机确认界面",
        "视觉通道",
        "配置钩子"
    ],
    "delegation_hops_grid": [
        1,
        2,
        3
    ],
    "authorization_mode": "名称+schema 静态门",
    "capability_class": "none",
    "prompt_composition": "compound",
    "turns": 1,
    "custom_logic_required": False,
    "distinctness_axis": "mechanism_first_step"
}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {
    "mechanism": "LIT-B-58",
    "mechanism_source": "B-58 arXiv:2604.21477v1 §5.3（Objective Validators）与 §6.1（benchmark-scale runtime ASR，2,579 条用例）",
    "vector": "工具返回",
    "technique": "手工设计",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-58 arXiv:2604.21477v1 §5.3（Objective Validators）与 §6.1（benchmark-scale runtime ASR，2,579 条用例）",
        "B-58 摘要：总体 ASR 31.9%；多模态注入 38.7% / puppet 34.5% / tool poisoning 22.6%",
        "B-58 Table 1（Runtime ASR across models, attack families, prompt composition modes；ASR 31.9% over 2,579 条）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-58",
        "locator": "B-58 arXiv:2604.21477v1 §5.3（Objective Validators）与 §6.1（benchmark-scale runtime ASR，2,579 条用例）；B-58 摘要：总体 ASR 31.9%；多模态注入 38.7% / puppet 34.5% / tool poisoning 22.6%",
        "value": "LIT-B-58"
    },
    "verifier": "ground_truth_contradiction",
    "evidence_layer": "state",
    "negative_control": "T03.B-45.mcp_upd_toolchain_composition"
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T03.spec_from_card(METHOD_ID)
    spec.delivery.delegation_hops = PARAMS["delegation_hops_grid"][0]
    spec.delivery.privilege_surface = PARAMS["privilege_surface_grid"][0]

    if "--params" in argv:
        print(json.dumps({"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        plans = T03.plan_grid(spec) if "--grid" in argv else [T03.build_plan(spec)]
        print(json.dumps(plans if "--grid" in argv else plans[0],
                         ensure_ascii=False, indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
