#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T06 派生脚本生成器：由 T06.py + 每张卡的参数，确定性派生脚本。

用法: python methods/T06/gen_scripts.py
输出: methods/T06/scripts/<mechanism_ref>_<slug>.py
"""
import io
import importlib.util as ilu
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLASS_MODULE = HERE / "T06.py"
CARDS = HERE / "cards"
OUT = HERE / "scripts"

_spec = ilu.spec_from_file_location("_t06mod", CLASS_MODULE)
_mod = ilu.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)
ENTRY_TOOL = _mod.ENTRY_TOOL
NON_PARAMETRIC = _mod.NON_PARAMETRIC
SIDE_CHANNEL = _mod.SIDE_CHANNEL_METHODS

HEADER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{title}

派生自 methods/T06/T06.py + 卡 {mid}（源/派生两层结构，见 docs/delivery-form.md）。
本文件是构造规格，不是成品载荷：不含载荷正文、不含真实凭据（禁令 9 / 标准 S4）。

用法:
  python {fname} --plan         # 打印执行计划（不执行）
  python {fname} --plan --grid  # 按维度档位展开参数网格
  python {fname} --params       # 打印参数与引用块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T06  # noqa: E402

METHOD_ID = "{mid}"

#: 参数：档位可变项（S3）
PARAMS = {params}

#: 引用块：关键构造对回卡上 provenance_components（S2）
REFERENCE = {reference}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = T06.spec_from_card(METHOD_ID)
    spec.probe.budget = PARAMS["budget_grid"][0]
    spec.turns_grid = PARAMS["turns_grid"]

    if "--params" in argv:
        print(json.dumps({{"method_id": METHOD_ID, "params": PARAMS,
                           "reference": REFERENCE}}, ensure_ascii=False, indent=1))
    elif "--plan" in argv:
        print(json.dumps(T06.plan_grid(spec) if "--grid" in argv else T06.build_plan(spec),
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
        args = (c.get("execution") or {}).get("args") or {}
        params = {
            "entry_point": vec,
            "entry_tool": ENTRY_TOOL.get(vec, "user_turn"),
            "artifact_kind": c.get("carrier", "text_only"),
            "budget_grid": args.get("budget_grid") or [1, 10, 50],
            "turns_grid": [1, 3, 5],
            "turns": c.get("turns", 1),
            "dimensions": c.get("dimensions") or [],
            "side_channel": mid in SIDE_CHANNEL,
            "custom_logic_required": mid in NON_PARAMETRIC,
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
            "bib_id": (c["source_refs"] or [""])[0][:8],
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