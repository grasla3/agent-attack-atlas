import io, sys, pathlib
ROOT = pathlib.Path(r"外部组件")
sys.path.insert(0, str(ROOT))
from tools import cardcheck as CC
ctx = CC.Ctx(ROOT)
rules = ctx.schema["x-validation-rules"]
L = ["# 规则索引（`docs/rule-index.md`）", "",
     "| 项 | 值 |", "|---|---|",
     "| 生成方式 | 由 `tools/gen_rule_index.py` 从 schema + `cardcheck.RULES` 生成 |",
     "| 为什么需要 | **规则编号不是稳定标识符**——新增规则会使其后所有编号位移。"
     "各类会话引用规则时应带 `rule_id`，不要只写编号 |",
     "| 当前 | schema 声明 **%d** 条 |" % len(rules), "",
     "| # | rule_id（稳定） | 状态 | 规则摘要 |", "|---|---|---|---|"]
for i in sorted(CC.RULES):
    rid, _fn, status, _why = CC.RULES[i]
    L.append("| %d | `%s` | %s | %s |" % (i, rid, status, rules[i-1][:88].replace("|", "\\|")))
out = ROOT/"docs"/"rule-index.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
print("修 3：docs/rule-index.md 已生成（%d 条）" % len(CC.RULES))
