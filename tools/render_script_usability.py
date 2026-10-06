# -*- coding: utf-8 -*-
"""生成 report/script-usability.md —— **攻击方法脚本集**的质量与可用性台账。
数据源：report/script-usability-ledger.json（离线、确定性）+ report/per-class-measured-coverage.json（实测）。"""
import io, json, os, sys, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, 'report', 'script-usability-ledger.json'), encoding='utf-8'))
M = json.load(open(os.path.join(ROOT, 'report', 'per-class-measured-coverage.json'), encoding='utf-8'))
rows = L['rows']
TITLE = {'T01': '记忆与知识污染', 'T02': '审计与日志破坏', 'T03': '权限与授权提升',
         'T04': '物理/具身动作', 'T05': '工具与技能投毒', 'T06': '提示词与系统信息外泄',
         'T07': '资源与成本耗尽', 'T08': '敏感数据外泄'}
CASES = sorted(TITLE)

def n(pred):
    return sum(1 for r in rows if pred(r))

out = []
out.append('# 攻击方法脚本集：质量与可用性台账')
out.append('')
out.append('> 产物是**攻击方法脚本集**；实测与评分都为它服务。本文件是**脚本自己**的台账。')
out.append('> 由 `tools/script_usability_ledger.py` 离线、确定性地生成（**不依赖 LLM、不依赖判据**），')
out.append('> 再由 `tools/render_script_usability.py` 排版。实测那一半见 `report/per-class-measured-coverage.md`。')
out.append('')
out.append('## 一、全库结论（可直接引用）')
out.append('')
out.append('| 指标 | 值 | 说明 |')
out.append('|---|---:|---|')
out.append('| 方法卡总数 | %d | 8 类 |' % len(rows))
out.append('| **有真实构造规格** | **%d / %d** | 不是 `scope="generic"` 那条兜底探针 |' % (n(lambda r: r['spec'] != 'absent'), len(rows)))
out.append('| 规格待补（模块自报 `PAYLOAD_SPEC_PENDING`） | %d | **显式登记**，不静默回落 |' % n(lambda r: r['spec'] == 'pending'))
out.append('| **静默回落成兜底** | **%d** | 必须为 0：G-6 的病根就是这一步以前是静默的 |' % n(lambda r: r['spec'] == 'absent'))
out.append('| **给一个入口面齐全的靶标即可组装** | **%d / %d** | 脚本自身的质量 |' % (n(lambda r: r.get('assembles')), len(rows)))
out.append('| 对抗臂与对照臂载荷**不同文** | %d | 两臂同文会让 `Adv̂` 恒为 0（见下） |' % n(lambda r: r.get('arms_differ')))
out.append('| **对抗臂载荷与他卡共用** | **0 组** | 逐卡正文 SHA 去重（149 张可组装的卡两两不同） |')
out.append('| **对照臂载荷与他卡共用** | **31 组** | ⚠️ 2026-10-03 修正：早先只统计了对抗臂，把"0 组"误读成"两臂都专属"。实测对照臂**只有 73 段不同正文 / 149 张卡**，最大一组 **12 张共用**（`T05`）。机理：对照臂用的是族的**通用良性请求**，同族多张卡会落到同一句。⇒ **配对对照在这些格上不是逐卡定制**，读 `Adv̂` 时必须与配对臂的正确性一起看（`results/README.md` 可复算） |')
out.append('')
out.append('## 二、逐类：脚本 × 靶标')
out.append('')
out.append('| 类 | 名称 | 卡数 | 有规格 | 能组装 | 可投放靶标数 | 已测确定格 | 出过 `Adv̂>0` |')
out.append('|---|---|---:|---:|---:|---:|---:|---:|')
for case in CASES:
    sub = [r for r in rows if r['case'] == case]
    ok = [r for r in sub if r.get('assembles')]
    tg = collections.Counter()
    for r in ok:
        for t in (r.get('deliverable_targets') or []):
            tg[t] += 1
    det = sum(1 for x in M['cells'][case] if x.get('six_state') in ('pass', 'fail'))
    pos = sum(1 for x in M['cells'][case] if x.get('adv_hat') is not None and x['adv_hat'] > 0)
    best = max(tg.values()) if tg else 0
    out.append('| %s | %s | %d | %d | %d | %d | %d | %d |'
               % (case, TITLE[case], len(sub), sum(1 for r in sub if r['spec'] != 'absent'),
                  len(ok), best, det, pos))
out.append('')
out.append('## 三、「能组装」与「投得出去」是两件事 —— 逐靶标可投放')
out.append('')
targets = L['targets']
out.append('| 类 | ' + ' | '.join('`%s`' % t for t in targets) + ' |')
out.append('|---|' + '---:|' * len(targets))
for case in CASES:
    sub = [r for r in rows if r['case'] == case and r.get('assembles')]
    if not sub:
        out.append('| %s | ' % case + ' | '.join('—' for _ in targets) + ' |')
        continue
    cells = ['**%d/%d**' % (sum(1 for r in sub if r['per_target'].get(t)), len(sub)) for t in targets]
    out.append('| %s | ' % case + ' | '.join(cells) + ' |')
out.append('')
out.append('## 四、挡住脚本的就是那几个投放面')
out.append('')
need = collections.Counter()
for r in rows:
    for s in (r.get('requires') or []):
        need[s] += 1
have = set(L['surface_union'])
out.append('| 投放面 | 需要的卡数 | 现有靶标里有吗 |')
out.append('|---|---:|---|')
for s, c in need.most_common():
    out.append('| `%s` | %d | %s |' % (s, c, '有' if s in have else '**没有**'))
out.append('')
bad = [r for r in rows if not r.get('assembles')]
cc = collections.Counter(r['case'] for r in bad)
out.append('装不起来（给齐全面也装不起来）的 **%d 张**，逐类：%s。'
           % (len(bad), '、'.join('%s %d 张' % (k, v) for k, v in sorted(cc.items()))))
out.append('')
out.append('## 五、近似程度（卡上那个机制，是不是装出来的东西）')
out.append('')
out.append('| 类 | `scope=faithful` | `scope=approximation` | 近似裁定 |')
out.append('|---|---:|---:|---|')
for case in CASES:
    sub = [r for r in rows if r['case'] == case and r.get('assembles')]
    if not sub:
        continue
    sc = collections.Counter(r.get('scope') for r in sub)
    vd = collections.Counter(r.get('approximation_verdict') for r in sub)
    out.append('| %s | %d | %d | %s |' % (case, sc.get('faithful', 0), sc.get('approximation', 0),
                                          ' · '.join('%s %d' % (k, v) for k, v in sorted(vd.items()))))
out.append('')
out.append('## 六、不得由本台账推出的结论')
out.append('')
out.append('- 「能组装」**不等于**「有效果」。效果要真实批次（`runs/`），见 `report/per-class-measured-coverage.md`。')
out.append('- 「某靶标投不出去」**不是**脚本坏，是**靶标缺那个投放面**（逐靶标那一栏读）。')
out.append('- 「规格待补」是模块**自己登记**的待办，不是"忘了写"。')
out.append('- 本台账**不**用判据的成熟度评价脚本 —— 判据能不能判出来是另一回事。')
out.append('')
open(os.path.join(ROOT, 'report', 'script-usability.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('已写 report/script-usability.md（%d 行）' % len(out))
