#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查—使用不一致（压缩边界重链接）：检查时安全、使用时被重新链接为越权动作

派生自 methods/T03/T03.py + 卡 T03.B-48.relink_compression_boundary（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python T03_B-48_relink_compression_boundary.py --plan         # 打印执行计划（不执行）
  python T03_B-48_relink_compression_boundary.py --plan --grid  # 按维度档位展开
  python T03_B-48_relink_compression_boundary.py --params       # 打印参数与引用块
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

METHOD_ID = "T03.B-48.relink_compression_boundary"

#: 参数：档位可变项（S3）
PARAMS = {
    "entry_point": "检索文档",
    "entry_tool": "doc_ingest",
    "artifact_kind": "task_context",
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
    "mechanism": "LIT-B-48",
    "mechanism_source": "B-48 arXiv:2606.21732v1 Table 3（clean-split vs Relink，matched carrier）",
    "vector": "检索文档",
    "technique": "自动生成",
    "transform_chain": [
        "none"
    ],
    "provenance_kind": "interpolation",
    "source_grade": "B",
    "numeric_evidence": "original_table",
    "source_refs": [
        "B-48 arXiv:2606.21732v1 Table 3（clean-split vs Relink，matched carrier）",
        "B-48 Table 4/5/6（跨压缩 prompt / 压缩模型 / 后端模型的 RR 与下游 Backend Action）"
    ],
    "distinctness_evidence": {
        "axis": "mechanism_first_step",
        "ref": "LIT-B-48",
        "locator": "B-48 arXiv:2606.21732v1 Table 3（clean-split vs Relink，matched carrier）；B-48 Table 4/5/6（跨压缩 prompt / 压缩模型 / 后端模型的 RR 与下游 Backend Action）",
        "value": "LIT-B-48"
    },
    "verifier": "scenario_contract",
    "evidence_layer": "authorization",
    "negative_control": "T03.B-49.mas_hub_vertical_escalation"
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
