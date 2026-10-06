# -*- coding: utf-8 -*-
"""脚本可用性台账（v3）—— 修正两处判据来源：
· 规格在不在：看**真实调用** `spec_for_card()` 的回落结果（`scope == "generic"` 即无规格），
  不再自己按 `method_id` 查 `CONSTRUCTION_SPECS`（T06 按 `mechanism_ref` 存，那样查会假报"全无"）。
· 组装：对着「入口面齐全」判（脚本质量）与「逐靶标」判（脚本×靶标匹配）**分两栏**。
"""
import io, json, os, sys, glob, collections, hashlib, importlib, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = os.getcwd(); sys.path.insert(0, ROOT)
import yaml
from harness import payloads as P, runner as R

CASES = ['T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08']
TITLE = {'T01': '记忆与知识污染', 'T02': '审计与日志破坏', 'T03': '权限与授权提升',
         'T04': '物理/具身动作', 'T05': '工具与技能投毒', 'T06': '提示词与系统信息外泄',
         'T07': '资源与成本耗尽', 'T08': '敏感数据外泄'}

def target_caps():
    out = {}
    from harness.adapter_mcp_local import McpLocalTarget
    out['mcp-local'] = McpLocalTarget.__new__(McpLocalTarget).caps()
    for mod, cls, tid in (('harness.adapters.agentdojo_workspace', 'AgentDojoWorkspace', 'agentdojo-workspace'),
                          ('harness.adapters.agentdojo_banking', 'AgentDojoBanking', 'agentdojo-banking'),
                          ('harness.adapters.agentdojo_travel', 'AgentDojoTravel', 'agentdojo-travel')):
        C = getattr(importlib.import_module(mod), cls)
        out[tid] = C.__new__(C).caps()
    return out

CAPS = target_caps()
UNION = sorted({s for c in CAPS.values() for s in (c.get('entry_surfaces') or [])})
SUPER = {'entry_surfaces': UNION}
print('入口面并集（"齐全靶标"）:', UNION)
print()

rows = []
for case in CASES:
    mod = R.load_class_module(case)
    pending = getattr(mod, 'PAYLOAD_SPEC_PENDING', {}) or {}
    for cp in sorted(glob.glob('methods/%s/cards/*.yaml' % case)):
        stem = os.path.splitext(os.path.basename(cp))[0]
        card = yaml.safe_load(open(cp, encoding='utf-8'))
        mid = card.get('method_id') or stem
        r = {'case': case, 'stem': stem, 'method_id': mid,
             'mode': (card.get('execution') or {}).get('mode'),
             'verifier': (card.get('judge') or {}).get('verifier')}
        sp = P.spec_for_card(card, mod)
        meta = P.meta_of(sp) or {}
        r['spec'] = 'absent' if meta.get('scope') == 'generic' else (
            'pending' if mid in pending else 'present')
        if r['spec'] == 'pending':
            r['pending_note'] = str(pending[mid])[:90]
        r.update(frame=meta.get('frame'), carrier=meta.get('carrier'),
                 token_family=meta.get('token_family'), tokens=meta.get('tokens'),
                 scope=meta.get('scope'), requires=list(sp.effective_requires()), turns=sp.turns,
                 approximation_verdict=P.approximation_verdict(sp))
        try:
            adv = P.synthesize(sp, arm='adversarial', caps=SUPER)
            ctrl = P.synthesize(sp, arm='control', caps=SUPER)
            ctrl = P.synthesize(sp, arm='control', caps=SUPER)
            atext = adv if isinstance(adv, str) else "\n".join(adv or [])
            ctext = ctrl if isinstance(ctrl, str) else "\n".join(ctrl or [])
            r.update(assembles=True, payload_len=len(atext),
                     payload_sha=hashlib.sha256(atext.encode()).hexdigest()[:10],
                     ctrl_sha=hashlib.sha256(ctext.encode()).hexdigest()[:10],
                     arms_differ=(atext != ctext))
            r['per_target'] = {t: (not P.missing_requirements(sp, c)) for t, c in CAPS.items()}
            r['deliverable_targets'] = sorted(t for t, ok in r['per_target'].items() if ok)
        except Exception as e:
            r.update(assembles=False, assemble_error='%s: %s' % (type(e).__name__, str(e)[:140]))
        rows.append(r)

def table():
    print('=' * 112)
    print('【A/B】构造规格与"给一个入口面齐全的靶标时能不能组装"')
    print('=' * 112)
    print('%-6s %-22s %5s %7s %8s %7s %9s %9s' % ('类', '名称', '卡数', '规格在', 'PENDING', '全无', '能组装', '两臂不同'))
    print('-' * 112)
    for case in CASES:
        sub = [r for r in rows if r['case'] == case]
        c = collections.Counter(r['spec'] for r in sub)
        print('%-6s %-22s %5d %7d %8d %7d %9d %9d'
              % (case, TITLE[case], len(sub), c['present'], c['pending'], c['absent'],
                 sum(1 for r in sub if r.get('assembles')),
                 sum(1 for r in sub if r.get('arms_differ'))))
    print('-' * 112)
    c = collections.Counter(r['spec'] for r in rows)
    print('%-6s %-22s %5d %7d %8d %7d %9d %9d'
          % ('合计', '', len(rows), c['present'], c['pending'], c['absent'],
             sum(1 for r in rows if r.get('assembles')),
             sum(1 for r in rows if r.get('arms_differ'))))
table()

print()
print('=' * 112)
print('【D】逐靶标可投放（脚本 × 靶标匹配；缺面 = 该靶标投不出去，**不是**脚本坏）')
print('=' * 112)
print('%-6s %-22s %s' % ('类', '名称', '  '.join('%-20s' % t for t in sorted(CAPS))))
print('-' * 112)
for case in CASES:
    sub = [r for r in rows if r['case'] == case and r.get('assembles')]
    if not sub:
        print('%-6s %-22s （无可组装格）' % (case, TITLE[case])); continue
    print('%-6s %-22s %s' % (case, TITLE[case],
          '  '.join('%-20s' % ('%d/%d' % (sum(1 for r in sub if r['per_target'].get(t)), len(sub)))
                    for t in sorted(CAPS))))
print('-' * 112)
tot = [r for r in rows if r.get('assembles')]
print('%-6s %-22s %s' % ('合计', '%d 张能组装' % len(tot),
      '  '.join('%-20s' % ('%d/%d' % (sum(1 for r in tot if r['per_target'].get(t)), len(tot)))
                for t in sorted(CAPS))))
print()
need = collections.Counter()
for r in rows:
    for s in (r.get('requires') or []): need[s] += 1
print('  各卡声明的投放面（累计）:', dict(need))

print()
print('=' * 112)
print('【C】载荷专属性')
print('=' * 112)
print('【C】载荷专属性 —— **两臂分别统计**')
print('=' * 112)
print('⚠️ 2026-10-03 修正：早先这里只统计了**对抗臂**，于是"0 段共用"被误读成'
      '"两臂都专属"。实测（`results/README.md`）：'
      '**对抗臂 149/149 互不相同（0 组共用）**，而**对照臂只有 73 段不同正文、31 组共用**'
      '（最大一组 12 张卡共用同一条对照载荷）。')
print()
byhash = collections.defaultdict(list)
for r in rows:
    if r.get('payload_sha'): byhash[r['payload_sha']].append(r['method_id'])
dups = {k: v for k, v in byhash.items() if len(v) > 1}
for case in CASES:
    sub = [r for r in rows if r['case'] == case and r.get('payload_sha')]
    print('  %-6s %3d 张 → %3d 段不同正文' % (case, len(sub), len({r['payload_sha'] for r in sub})))
print('  **对抗臂**：全库共用正文的组数 :', len(dups))
for k, v in sorted(dups.items())[:8]: print('     %s : %s' % (k, v))
# —— 对照臂：另算一遍 ——
ctrl = collections.defaultdict(list)
for r in rows:
    if r.get('ctrl_sha'): ctrl[r['ctrl_sha']].append(r['method_id'])
cdups = {k: v for k, v in ctrl.items() if len(v) > 1}
print()
print('  **对照臂**：可组装 %d 张 → %d 段不同正文；**共用正文的组数 %d**'
      % (sum(len(v) for v in ctrl.values()), len(ctrl), len(cdups)))
for k, v in sorted(cdups.items(), key=lambda x: -len(x[1]))[:6]:
    print('     %s (%d 张) : %s' % (k, len(v), v[:6] + (['…'] if len(v) > 6 else [])))

print()
print('=' * 112)
print('【E】近似程度')
print('=' * 112)
for case in CASES:
    sub = [r for r in rows if r['case'] == case and r.get('assembles')]
    if not sub: continue
    print('%-6s scope=%-54s verdict=%s' % (case,
          str(dict(collections.Counter(r.get('scope') for r in sub))),
          dict(collections.Counter(r.get('approximation_verdict') for r in sub))))

print()
print('=' * 112)
print('【B2】装不起来的卡')
print('=' * 112)
bad = [r for r in rows if not r.get('assembles')]
print('  共 %d 张（占 %.1f%%）' % (len(bad), 100.0 * len(bad) / len(rows)))
cc = collections.Counter()
for r in bad:
    m = re.search(r'未声明所需投放面：(.*?)（', r.get('assemble_error') or '')
    cc[m.group(1) if m else (r.get('assemble_error') or '')[:40]] += 1
for k, v in cc.most_common():
    print('     %-22s %d 张' % (k, v))
print('  逐类 :', dict(collections.Counter(r['case'] for r in bad)))

out = {'schema': 'script-usability-ledger-v3',
       'note': '离线、确定性；不依赖 LLM 与判据。效果见 runs/ 与 report/per-class-measured-coverage.md',
       'surface_union': UNION, 'targets': sorted(CAPS), 'rows': rows}
with open('report/script-usability-ledger.json', 'w', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print()
print('已写 report/script-usability-ledger.json')
