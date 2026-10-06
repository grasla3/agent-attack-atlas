# -*- coding: utf-8 -*-
"""攻击脚本实测进度：逐类 × 五级口径。从批次汇总重建（随包 `results/batches/` 优先）。"""
import io, sys, os, glob, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd(); sys.path.insert(0, ROOT)
import yaml

cards = collections.defaultdict(list)
for p in glob.glob("methods/T0*/cards/*.yaml"):
    cls = os.path.basename(os.path.dirname(os.path.dirname(p)))
    cards[cls].append(os.path.splitext(os.path.basename(p))[0])

def _summaries():
    """批次汇总的来源：随包的 `results/batches/` 优先，本地运行目录 `runs/` 兜底。"""
    got = sorted(glob.glob("results/batches/*.summary.json"))
    return got or sorted(glob.glob("runs/*/summary.json"))


def ck(cls, stem):
    s = stem.replace(".", "_")
    if s.startswith(cls + "_"): s = s[len(cls) + 1:]
    for pre in ("LIT-B-", "AUD-", "B-"):
        if s.startswith(pre): s = s[len(pre):]; break
    m = re.match(r"^([^_]+)_(.*)$", s)
    return (cls, m.group(1), m.group(2)) if m else (cls, s, "")
K = {}
for cls, ss in cards.items():
    for st in ss: K[ck(cls, st)] = (cls, st)

seen, determ, pos = set(), collections.defaultdict(set), collections.defaultdict(set)
nadv = {}
for sj in _summaries():
    try: s = json.load(open(sj, encoding="utf-8"))
    except Exception: continue
    for c in (s.get("detail") or []):
        mid = c.get("method_id") or ""
        if "." not in mid: continue
        cls, _, rest = mid.partition(".")
        hit = K.get(ck(cls, rest))
        if not hit: continue
        st = hit[1]
        if (c.get("n_adv") or 0) + (c.get("n_ctrl") or 0) > 0: seen.add((cls, st))
        if c.get("six_state") in ("pass", "fail"): determ[cls].add(st)
        if c.get("adv_hat") is not None and c["adv_hat"] > 0: pos[cls].add(st)

# 可跑（三道闸门 + 已知第四道 class_status 的上界）
sys.path.insert(0, ROOT)
from score.targets import expand_tools, load_aliases
from harness import payloads as P, runner as R
import importlib
AL = load_aliases()
A = {"mcp-local": ("harness.adapter_mcp_local", "McpLocalTarget"),
     "agentdojo-workspace": ("harness.adapters.agentdojo_workspace", "AgentDojoWorkspace"),
     "agentdojo-banking": ("harness.adapters.agentdojo_banking", "AgentDojoBanking"),
     "agentdojo-travel": ("harness.adapters.agentdojo_travel", "AgentDojoTravel")}
have, dim, surf = {}, {}, {}
for tid, (m, c) in A.items():
    C = getattr(importlib.import_module(m), c); inst = C.__new__(C)
    have[tid], _ = expand_tools({"target_id": tid, "tools": inst.tools()}, tid, AL)
    dim[tid] = json.load(open("targets/%s.json" % tid, encoding="utf-8")).get("design_dimensions") or {}
    surf[tid] = set((inst.caps() or {}).get("entry_surfaces") or [])
runnable = collections.defaultdict(set)
for case in sorted(cards):
    mod = R.load_class_module(case)
    for st in cards[case]:
        p = "methods/%s/cards/%s.yaml" % (case, st)
        d = yaml.safe_load(open(p, encoding="utf-8"))
        needs = [str(x) for x in ((d.get("trigger_path") or {}).get("required_actions") or [])]
        pre = d.get("preconditions") or {}
        try: reqs = set(P.spec_for_card(d, mod).effective_requires())
        except Exception: reqs = {"<装不起来>"}
        for tid in A:
            if (not [x for x in needs if x not in have[tid]]) and \
               (not [k for k, v in pre.items() if dim[tid].get(k, 0) < v]) and \
               (not (reqs - surf[tid])):
                runnable[case].add(st); break

print("=" * 72)
print("攻击脚本实测进度（逐类）")
print("=" * 72)
print("%-5s %5s %8s %9s %10s %11s" % ("类", "卡数", "可跑", "真跑过", "有确定判定", "Adv̂>0(卡)"))
print("-" * 72)
T = collections.Counter()
for case in sorted(cards):
    n = len(cards[case])
    r = len(runnable[case]); s = len([1 for (c, st) in seen if c == case])
    d = len(determ[case]); pz = len(pos[case])
    T.update(dict(cards=n, runnable=r, seen=s, determ=d, pos=pz))
    print("%-5s %5d %8d %9d %10d %11d" % (case, n, r, s, d, pz))
print("-" * 72)
print("%-5s %5d %8d %9d %10d %11d" % ("合计", T["cards"], T["runnable"], T["seen"], T["determ"], T["pos"]))
print()
print()
print("⚠️ 上面那张「Adv̂>0(卡)」表按 `(类,卡)` 去重但**未按靶标分**；")
print("   要引用请以 `report/per-class-measured-coverage.md` 的分层表为准。")
print("Adv̂>0 的卡（逐张）：")
for case in sorted(pos):
    if pos[case]:
        for st in sorted(pos[case]): print("   %-5s %s" % (case, st))


print()
print("=" * 92)
print("逐格明细（有确定判定或 Adv̂>0 的格）")
print("=" * 92)
print("⚠️ 本节**未按键去重**：同一格在多个批次里出现过就会重复列，")
print("   故其 Adv̂>0 的**计数不可直接引用**；要口径干净的逐格数请用")
print("   `report/per-class-measured-coverage.md`（那份每格取最新一次）。")
rows = []
for sj in _summaries():
    try: ss = json.load(open(sj, encoding="utf-8"))
    except Exception: continue
    for c in (ss.get("detail") or []):
        mid = c.get("method_id") or ""
        if "." not in mid: continue
        cls, _, rest = mid.partition(".")
        hit = K.get(ck(cls, rest))
        if not hit: continue
        if c.get("six_state") in ("pass", "fail") or (c.get("adv_hat") or 0) > 0:
            rows.append((cls, hit[1].split(".", 1)[-1][:40], ss.get("target_id"),
                         c.get("six_state"), c.get("v_adv"), c.get("v_ctrl"),
                         c.get("adv_hat"), ss.get("n")))
rows.sort()
for cls, nm, tgt, st, va, vc, ah, n in rows:
    print("%-5s %-42s %-22s %-6s n=%-3s v_adv=%-6s v_ctrl=%-6s Adv^=%s" % (
        cls, nm, tgt, st, n, va, vc, ah))
print()
print("共", len(rows), "格")
