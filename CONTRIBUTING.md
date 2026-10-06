# 参与贡献

## 先跑通这三条

```powershell
pip install -r requirements.txt
python tools\cardcheck.py              # 校验 methods/ 下的全部方法卡（47 条规则）
python -m unittest discover -s tests   # 1602 条单元测试
python tools\gates.py --gate 0         # 10 项提交前检查
```

提交请走带门禁的包装器（Git 钩子在部分 Windows 环境下不会执行）：

```powershell
python tools\gate_commit.py -m "feat(methods): ..."
```

门禁不通过即拒绝提交。它拦的几类问题（凭据、绝对路径、负向断言、文件清单漂移）都真实发生过。

## 新增一个方法

1. **先找文献。** 方法必须来自公开工作，在 docs/domain-and-literature.md 登记出处，写明图号、表号或章节。
2. **写卡。** 在 `methods/T0X/cards/` 下新建 YAML，按同目录已有卡的字段填写：机制出处、
   注入通道、前置条件、触发条件、可观测后果，以及一条与之配对的良性载荷。
   `python tools\cardcheck.py` 会逐条报出缺项。
3. **写构造规格。** 在 `methods/T0X/T0X.py` 的 `CONSTRUCTION_SPECS` 中加一条，声明载体、
   框架、槽取值与 `scope`。`scope="generic"` 是兜底，不得当作该方法的效果。
4. **选判据。** 卡上的 `judge.verifier` 必须是 `judges/registry.json` 中已有的判据。
   若没有判据能覆盖该构念，不要硬套，另写判据并配反例测试。
5. **先跑小样本。** 从 n=3 起，先确认装置走得通（投放面存在、判据观测可达），再加样本量。

## 新增一个靶标

实现 `harness/protocol.py` 的适配器接口（`reset` / `inject` / `run_task` / `observe` / `caps`），
并在 `targets/` 下登记目标信息与能力别名。

`caps()` 必须如实声明本靶标能提供什么。声明了却给不出的观测，会让判据把"没测到"读成"没发生"，
这类错误在报告上极难发现。

## 新增判据时的评审清单

判据上线前，逐条确认：

* **方向一致**：判据判为 `pass` 的条件，必须与卡上 `observable_as` 声明的观测量同一个方向。
  方向接反时，对照臂会稳定判 `pass`，`Adv̂` 不可能为正。
* **可表达**：判据要求的每个参数或键，必须在该靶标公布的接口里是可提交的。
  靶标公布的 schema 禁止该键时，模型无法合规地填它，构念不可能被实例化。
* **可达**：方法的最短执行路径必须落在单轮工具循环上限之内。路径更长时，
  模型会在抵达目标动作之前被截断，判据只会看到"什么都没发生"。
* **可判**：判据在正常与异常两种观测下都应给出 `pass` 或 `fail`；只能给出 `inconclusive` 的
  判据不构成测量能力。
* **可复算**：判据的全部输入必须落进 `trial-*.json`。

## 几条不是风格问题的纪律

* **不要为了数字好看去改判定标准。** 装置缺陷该修；判据口径要改，先写清原口径错在哪里。
* `Adv̂ ≤ 0` 不声称方法有效；`untested ≠ 0`；`inconclusive` 不是失败。
* 判据的输入必须逐试验落盘，否则判据改动后旧证据复算不出来。
* 凭据只走环境变量，仓库内不放密钥。
* 每个数字给批次 id 与复算命令。

## 报告问题

安全与披露渠道见 `SECURITY.md`。