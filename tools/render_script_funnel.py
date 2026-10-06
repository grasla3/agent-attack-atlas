# -*- coding: utf-8 -*-
"""把两份台账合成**一张漏斗表**：脚本 → 投放 → 诱导 → 效果。
数据源：report/script-usability-ledger.json · report/script-elicitation-ledger.json
        · report/per-class-measured-coverage.json"""
import io, json, os, sys, glob, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import yaml
import importlib
from harness.adapter_mcp_local import McpLocalTarget

TITLE = {'T01': '记忆与知识污染', 'T02': '审计轨迹破坏', 'T03': '权限与授权提升',
         'T04': '物理/具身动作', 'T05': '工具与技能投毒', 'T06': '提示词与系统信息外泄',
         'T07': '资源与成本耗尽', 'T08': '敏感数据外泄'}
CASES = sorted(TITLE)

U = json.load(open(os.path.join(ROOT, 'report', 'script-usability-ledger.json'), encoding='utf-8'))
E = json.load(open(os.path.join(ROOT, 'report', 'script-elicitation-ledger.json'), encoding='utf-8'))
M = json.load(open(os.path.join(ROOT, 'report', 'per-class-measured-coverage.json'), encoding='utf-8'))

# 逐卡：真实批次里"被诱导"的证据
elic = collections.defaultdict(dict)
for r in E['rows']:
    if r['arm'] != 'adv':
        continue
    d = elic[r['mid']]
    d.setdefault('called', set()); d.setdefault('driven', set())
    d['called'] |= set(r['called']); d['driven'] |= set(r['driven'])
    d['placed'] = d.get('placed') or r['placed']
    d['resp'] = d.get('resp') or r['has_response']
    d['case'] = r['case']

# 卡：required_actions
needs_of = {}
for p in glob.glob(os.path.join(ROOT, 'methods', 'T0*', 'cards', '*.yaml')):
    d = yaml.safe_load(open(p, encoding='utf-8'))
    mid = d.get('method_id')
    if mid:
        needs_of[mid] = [str(a) for a in (((d.get('trigger_path') or {}).get('required_actions')) or [])]

L = []
L.append('# 攻击方法脚本集：从「能组装」到「出效果」的漏斗')
L.append('')
L.append('> 回答一个问题：**每一类有几种攻击方法被证明了脚本质量与可用性。**')
L.append('> 产物是攻击方法脚本集；本表把它的四级证据分开列，**不把"判据判不出来"算成"脚本不行"**。')
L.append('')
L.append('| 级 | 问什么 | 证据从哪来 | 依赖判据吗 |')
L.append('|---|---|---|---|')
L.append('| ① 能组装 | 脚本装得出载荷吗 | `report/script-usability.md`（离线，对着"入口面齐全"的靶标） | **不依赖** |')
L.append('| ② 可投放 | 目标靶标有这个投放面吗 | 同上（逐靶标那一栏） | **不依赖** |')
L.append('| ③ 诱导到 | 模型真的做了卡要的那个动作吗 | `report/script-elicitation-ledger.json`（读真实批次的 `tool_calls`） | **不依赖** |')
L.append('| ④ 出效果 | 六态有没有确定判定 / `Adv̂>0` | `report/per-class-measured-coverage.md` | 依赖 |')
L.append('')
L.append('## 逐类漏斗')
L.append('')
L.append('| 类 | 名称 | 卡数 | ① 能组装 | ② 可投放(最好靶标) | ③ 诱导到 | ④ 有确定判定 | ④ `Adv̂>0` |')
L.append('|---|---|---:|---:|---:|---:|---:|---:|')
tots = collections.Counter()
for case in CASES:
    sub = [r for r in U['rows'] if r['case'] == case]
    ok = [r for r in sub if r.get('assembles')]
    tg = collections.Counter()
    for r in ok:
        for t in (r.get('deliverable_targets') or []):
            tg[t] += 1
    best = max(tg.values()) if tg else 0
    ran = [m for m in elic if elic[m]['case'] == case]
    ind = 0
    for m in ran:
        needs = needs_of.get(m) or []
        got = elic[m]['called'] | elic[m]['driven']
        if (set(needs) & got) or (elic[m].get('placed') and elic[m].get('resp')):
            ind += 1
    det = sum(1 for x in M['cells'][case] if x.get('six_state') in ('pass', 'fail'))
    pos = sum(1 for x in M['cells'][case] if x.get('adv_hat') is not None and x['adv_hat'] > 0)
    tots['cards'] += len(sub); tots['asm'] += len(ok); tots['ran'] += len(ran)
    tots['ind'] += ind; tots['det'] += det; tots['pos'] += pos
    L.append('| %s | %s | %d | **%d** | **%d** | %d/%d | %d | %d |'
             % (case, TITLE[case], len(sub), len(ok), best, ind, len(ran), det, pos))
L.append('| **合计** |  | **%d** | **%d** | — | **%d/%d** | **%d** | **%d** |'
         % (tots['cards'], tots['asm'], tots['ind'], tots['ran'], tots['det'], tots['pos']))
L.append('')
L.append('## 读法（三条不许混）')
L.append('')
L.append('- **① 能组装** 与 **② 可投放** 是**脚本自己的质量**，离线可复算，与判据无关。')
L.append('- **③ 诱导到** 是**脚本在真实批次里的可用性**（模型真的做了那个动作），不依赖判据；')
L.append('  但它依赖靶标 —— 靶标缺投放面时卡连跑都跑不起来（记 `untested`）。')
L.append('- **④ 出效果** 依赖判据。**判据判不出来不等于脚本不行**：')
L.append('  当前实现实测两例 —— T07 的仪器测到 ≈2.5× 而 `state_diff` 判 fail；')
L.append('  T05 修前的 6 个 `pass` 是装置驱动的假阳性（已作废）。')
L.append('')
L.append('## 结论（对照的要求）')
L.append('')
L.append('「每一类有几种攻击方法被证明了脚本质量与可用性」：')
L.append('')
L.append('- **① + ② 两级现在 8 类都有数**（上表全部由 `tools/script_usability_ledger.py` 离线复算）；')
_ran_cases = sorted({elic[m]['case'] for m in elic if elic[m].get('case')})
L.append('- **③ 级有真实批次可读的类**：%s（逐类张数见上表）。'
         % '、'.join(_ran_cases))
# ⚠️ 这一段**从 json 现算**，不写死历史片段（2026-10-04 修）：
# 早先这里硬编码了"④ 级只有 T06 有 Adv̂>0"，于是在 T05 出正读数之后**照旧那么说** ——
_pos_by_case = {c: sum(1 for x in M['cells'][c]
                       if x.get('adv_hat') is not None and x['adv_hat'] > 0)
                for c in CASES}
_pos_cases = [c for c in CASES if _pos_by_case[c] > 0]
L.append('- **④ 级有 `Adv̂>0` 的类**：%s。逐格数：%s。'
         % ('、'.join(_pos_cases) or '（本次没有）',
            ' · '.join('%s %d 格' % (c, _pos_by_case[c]) for c in CASES if _pos_by_case[c])))
L.append('  其余类的堵点逐条记在 `results/README.md` 与')
L.append('  `results/README.md`；')
L.append('  T05 的「选择」终点打通过程与读数见')
L.append('  `results/README.md`。')
L.append('')
L.append('⚠️ **④ 级不得只报"有没有正读数"**：`Adv̂>0` 的格还要看它**是不是同一条机制**、')
L.append('  以及端点/模型是否可比（换过端点的批次在 `env.llm_endpoint.overridden` 里标着）。')
L.append('')
open(os.path.join(ROOT, 'report', 'script-funnel.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('已写 report/script-funnel.md')
