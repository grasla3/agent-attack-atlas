#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T07 派生脚本生成器：对 cards/ 里每张卡生成 scripts/<同名>.py（缺哪张补哪张）。

脚本形态与 methods/T07/scripts/ 下既有 26 份一致：只声明构造规格，不夹带载荷正文（S4）。
用法：python methods/T07/gen_scripts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")
M = Path(__file__).resolve().parent
TPL = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T07 派生脚本 · {mid}

由 methods/T07/T07.py（类模块，手写） + 本卡参数**派生**而成（methods/T07/gen_scripts.py）。
同一参数生成同一份（docs/delivery-form.md §1）。

用法：
  python {rel} --plan            # 打印执行计划（不执行）
  python {rel} --plan --grid     # 按维度档位展开
  python {rel} --validate        # 结构校验

S4 / 禁令 9：本脚本**不含任何载荷正文**，args 里只有结构性参数
（入口 / 目标组件 / 探针类别 / 剂量 / 位置 / 轮次）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from T07 import build_plan, plan_grid, spec_from_card, validate  # noqa: E402

METHOD_ID = "{mid}"
PARAMS = {params}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = spec_from_card(METHOD_ID)
    if "--validate" in argv:
        errs = validate(spec)
        print(json.dumps({{"method_id": METHOD_ID, "ok": not errs, "errors": errs}},
                         ensure_ascii=False, indent=1))
        return 0 if not errs else 1
    plans = plan_grid(spec) if "--grid" in argv else [build_plan(spec)]
    print(json.dumps(plans if "--grid" in argv else plans[0], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

n = 0
for p in sorted((M / "cards").glob("*.yaml")):
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    slug = c["method_id"].split(".", 2)[2]
    out = M / "scripts" / ("T07_%s_%s.py" % (c["mechanism_ref"], slug))
    if out.exists():
        continue
    out.write_text(TPL.format(mid=c["method_id"],
                              rel="methods/T07/scripts/" + out.name,
                              params=json.dumps(c["execution"]["args"], ensure_ascii=False)),
                   encoding="utf-8", newline="\n")
    print("script:", out.name)
    n += 1
print("新增脚本:", n)