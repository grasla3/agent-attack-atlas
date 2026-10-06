# -*- coding: utf-8 -*-
"""**脚本诱导台账**：脚本把模型逼到"做那个动作"了吗？

⚠️ 口径（本版修正）：卡声明的 `required_actions` 大多**不是工具调用**
（T06/T07 是 `user_turn` / `response_generate` / `generation_complete`，T01 是
`retrieval_corpus_ipi` 这类抽象动作）。拿"工具调用"去对它们必然全 0 —— 那不是
脚本没生效，是**度量对错了动作**。故本表分两栏：

  · **工具调用类**：`required_actions` 里含真实工具名的卡（T02/T03/T05/T08 的一部分），
    度量 = 那些工具名有没有出现在 `tool_calls` 里；
  · **对话轮类**：其余卡，度量 = 载荷有没有真的投进去（`turns` / `placed`），
    以及模型有没有产生回复（`response_text` 非空）。**不拿工具调用去要求它们。**

两栏都**只回答"被诱导了没有"**，不回答"有没有效果"（效果要判据，见实测台账）。
"""
import io, json, os, sys, glob, collections, importlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = os.getcwd(); sys.path.insert(0, ROOT)
import yaml

tool_names = set()
from harness.adapter_mcp_local import McpLocalTarget
try:
    tool_names |= set(McpLocalTarget.__new__(McpLocalTarget).tools())
except Exception:
    pass
for mod, cls in (('harness.adapters.agentdojo_workspace', 'AgentDojoWorkspace'),
                 ('harness.adapters.agentdojo_banking', 'AgentDojoBanking'),
                 ('harness.adapters.agentdojo_travel', 'AgentDojoTravel')):
    C = getattr(importlib.import_module(mod), cls)
    try:
        tool_names |= set(C.__new__(C).tools())
    except Exception:
        pass

cards = {}
for p in glob.glob('methods/T0*/cards/*.yaml'):
    d = yaml.safe_load(open(p, encoding='utf-8'))
    mid = d.get('method_id')
    if not mid: continue
    needs = [str(a) for a in (((d.get('trigger_path') or {}).get('required_actions')) or [])]
    cards[mid] = {'case': mid.split('.')[0], 'needs': needs,
                  'tool_needs': [a for a in needs if a in tool_names],
                  'dialogue_needs': [a for a in needs if a not in tool_names]}

rows = []
for f in glob.glob('runs/*/*/*/trial-*.json') + glob.glob('runs/*/*/*/*/trial-*.json'):
    try:
        t = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    mid = t.get('method_id') or ''
    if mid not in cards: continue
    called = {str(c.get('tool')) for c in (t.get('tool_calls') or []) if isinstance(c, dict)}
    driven = set()
    for r in (t.get('receipts') or []):
        if isinstance(r, dict) and r.get('kind') == 'mcp_local_construct':
            driven |= set(r.get('driven_actions') or [])
    rows.append({'mid': mid, 'case': cards[mid]['case'],
                 'arm': 'ctrl' if f.endswith('-control.json') else 'adv',
                 'target': t.get('target_id'), 'called': sorted(called),
                 'driven': sorted(driven),
                 'turns': t.get('turns'),
                 'has_response': bool((t.get('response_text') or '').strip()),
                 'placed': bool(t.get('turns'))})

agg = collections.defaultdict(list)
for r in rows: agg[r['mid']].append(r)

print('=' * 112)
print('【一】工具调用类：卡要的工具名有没有出现在 `tool_calls` 里')
print('=' * 112)
print('%-6s %6s %9s %9s %10s %12s' % ('类', '已跑卡', '要工具数', '被调用', '调用率', '整卡全调用'))
print('-' * 112)
T = collections.Counter(); H = {}; F = collections.Counter()
for case in sorted({c['case'] for c in cards.values()}):
    mids = [m for m in agg if cards[m]['case'] == case and cards[m]['tool_needs']]
    if not mids: continue
    n = h = fc = 0
    for m in mids:
        needs = cards[m]['tool_needs']
        got = set()
        for r in agg[m]:
            if r['arm'] != 'adv': continue
            got |= set(r['called']) | set(r['driven'])
        n += len(needs); k = sum(1 for a in needs if a in got); h += k
        if k == len(needs): fc += 1
    T[case] = len(mids); H[case] = (n, h); F[case] = fc
    print('%-6s %6d %9d %9d %9s %12s' % (case, len(mids), n, h,
          ('%.1f%%' % (100.0*h/n)) if n else '—', '%d 张' % fc))
print('-' * 112)
tn = sum(v[0] for v in H.values()); th = sum(v[1] for v in H.values())
print('%-6s %6d %9d %9d %9s %12s' % ('合计', sum(T.values()), tn, th,
      ('%.1f%%' % (100.0*th/tn)) if tn else '—', '%d 张' % sum(F.values())))

print()
print('=' * 112)
print('【二】对话轮类：载荷投进去了吗、模型产生回复了吗（**不要求工具调用**）')
print('=' * 112)
print('%-6s %6s %10s %12s %12s' % ('类', '已跑卡', '投进去的卡', '有回复的卡', '投+回复的卡'))
print('-' * 112)
for case in sorted({c['case'] for c in cards.values()}):
    mids = [m for m in agg if cards[m]['case'] == case and cards[m]['dialogue_needs']]
    if not mids: continue
    adv = [r for r in agg[m] if r['arm'] == 'adv']
    pl = sum(1 for m in mids if any(r['placed'] for r in agg[m] if r['arm'] == 'adv'))
    rs = sum(1 for m in mids if any(r['has_response'] for r in agg[m] if r['arm'] == 'adv'))
    both = sum(1 for m in mids
               if any(r['placed'] and r['has_response'] for r in agg[m] if r['arm'] == 'adv'))
    print('%-6s %6d %10d %12d %12d' % (case, len(mids), pl, rs, both))

print()
print('=' * 112)
print('【三】工具调用类里**一次都没被调用**的卡（脚本这一步完全没生效）')
print('=' * 112)
for case in sorted({c['case'] for c in cards.values()}):
    zero = []
    for m in sorted(agg):
        if cards[m]['case'] != case or not cards[m]['tool_needs']: continue
        got = set()
        for r in agg[m]:
            if r['arm'] == 'adv': got |= set(r['called']) | set(r['driven'])
        if not (set(cards[m]['tool_needs']) & got): zero.append(m)
    if zero:
        print('  %s : %d 张' % (case, len(zero)))
        for m in zero[:6]:
            print('     %-50s 要 %s' % (m.split('.', 1)[1][:50], cards[m]['tool_needs']))

out = {'schema': 'script-elicitation-ledger-v2',
       'note': '只回答"被诱导了没有"；不回答"有没有效果"。工具调用类与对话轮类分开度量。',
       'tool_call_cases': {k: {'cards': T[k], 'needs': H[k][0], 'hit': H[k][1], 'full': F[k]}
                           for k in T},
       'rows': rows}
with open('report/script-elicitation-ledger.json', 'w', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print()
print('已写 report/script-elicitation-ledger.json')
