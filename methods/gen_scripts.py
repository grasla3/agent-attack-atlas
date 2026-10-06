#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由类模块 + 每张卡的参数，确定性派生 28 份方法脚本。

交付形态（docs/delivery-form.md §1）：脚本是交付物本身，由 T01.py + 参数生成。
保证"同参数生成同一份"，且结构上不含载荷正文（S4）。

用法: python methods/gen_scripts.py
"""
import io
import importlib.util as ilu
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
CLASS_MODULE = ROOT / "T01" / "T01.py"
CARDS = ROOT / "T01" / "cards"
OUT = ROOT / "T01" / "scripts"

#: 从类模块取常量，避免第二份真相
_spec = ilu.spec_from_file_location("_t01mod", CLASS_MODULE)
_mod = ilu.module_from_spec(_spec)
sys.modules[_spec.name] = _mod   # dataclass 解析注解时需要模块已注册
_spec.loader.exec_module(_mod)
ENTRY_TOOL = _mod.ENTRY_TOOL
NON_PARAMETRIC = _mod.NON_PARAMETRIC

HEADER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{title}

派生自 methods/T01/T01.py + 卡 {mid}（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python {fname} --plan         # 打印执行计划（不执行）
  python {fname} --plan --grid  # 按维度档位展开
  python {fname} --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T01  # noqa: E402

METHOD_ID = "{mid}"

#: 参数：档位可变项（S3）
PARAMS = {params}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {reference}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T01.spec_from_card(METHOD_ID)
    spec.injection.budget_grid = PARAMS["budget_grid"]
    spec.injection.placement_grid = PARAMS["placement_grid"]

    if "--params" in argv:
        print(json.dumps({{"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        plans = T01.plan_grid(spec) if "--grid" in argv else [T01.build_plan(spec)]
        print(json.dumps(plans if "--grid" in argv else plans[0],
                         ensure_ascii=False, indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def fmt(d) -> str:
    s = json.dumps(d, ensure_ascii=False, indent=4)
    return (s.replace(": true", ": True").replace(": false", ": False")
             .replace(": null", ": None"))


def main() -> int:
    import yaml
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for card in sorted(CARDS.glob("*.yaml")):
        c = yaml.safe_load(card.read_text(encoding="utf-8"))
        mid = c["method_id"]
        vec = c["provenance_components"]["vector"]
        vec = vec["ref"] if isinstance(vec, dict) else vec
        tech = c["provenance_components"]["technique"]
        tech = tech["ref"] if isinstance(tech, dict) else tech
        dims = c.get("dimensions") or []
        params = {
            "entry_point": vec,
            "write_tool": ENTRY_TOOL.get(vec, "kb_write"),
            "artifact_kind": c.get("carrier", "kb_doc"),
            "budget_grid": [1, 3, 5],
            "placement_grid": ["corpus_head", "corpus_tail", "scattered"],
            "granularity": "片段分解" if "poisoning_granularity" in dims else "单文档",
            "trigger": "休眠触发" if "retrieval_trigger" in dims else "常驻",
            "turns": c.get("turns", 1),
            "custom_logic_required": mid in NON_PARAMETRIC,
            "distinctness_axis": (c.get("distinctness_evidence") or {}).get("axis"),
        }
        reference = {
            "mechanism": c["mechanism_ref"],
            "mechanism_source": (c["provenance_components"]["mechanism"] or {}).get("source", ""),
            "vector": vec,
            "technique": tech,
            "transform_chain": c.get("transform_chain") or [],
            "provenance_kind": c.get("provenance_kind"),
            "source_grade": c.get("source_grade"),
            "numeric_evidence": c.get("numeric_evidence"),
            "source_refs": c.get("source_refs") or [],
            "distinctness_evidence": c.get("distinctness_evidence"),
            "verifier": c["judge"]["verifier"],
            "evidence_layer": c["judge"]["evidence_layer"],
            "negative_control": c["negative_control"]["method_id"],
        }
        fname = card.stem + ".py"
        body = HEADER.format(title=c["title"], mid=mid, fname=fname,
                             params=fmt(params), reference=fmt(reference))
        (OUT / fname).write_text(body, encoding="utf-8", newline="\n")
        n += 1
    print("派生脚本 %d 份 -> %s" % (n, OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
