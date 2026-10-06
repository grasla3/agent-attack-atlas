# 回退手册（`docs/rollback.md`）

> **目的**：改坏了能退回。本项目的产物大多是规范与数据，一次改错可能波及几十个文件；
> git 能回退，但前提是**你知道要退回哪个点**。快照就是那些点。

---

## 0. 三条铁律

| # | 铁律 |
|---|---|
| **1** | **动手改之前先打快照。** `gates.cmd snapshot` 或 `python tools/snapshot.py --label <描述>` |
| **2** | **每次提交都过门禁。** pre-commit 挂了不要习惯性 `--no-verify` |
| **3** | **回退前先看清单差异。** `python tools/snapshot.py --diff <tag>` 告诉你到底动了什么 |

---

## 1. 打快照

```powershell
# Windows
.\gates.cmd snapshot
.\gates.ps1 snapshot

# 带标签（推荐：标签要能看出「这是做 T01 之前的点」）
python tools\snapshot.py --label before-t01-cards
```

它做三件事：① 生成 `gate-manifest.json`（全部文件 SHA-256）② 有脏改动则先提交 ③ 打一个 annotated tag `snap-<时间戳>-<标签>`。

**列出全部快照**：

```powershell
python tools\snapshot.py --list
```

**看某快照之后动了什么**：

```powershell
python tools\snapshot.py --diff snap-20260929-143012-before-t01-cards
```

---

## 2. 四种回退场景

### 2.1 只改了工作区，还没提交

```powershell
git status                     # 先看动了什么
git checkout -- <path>         # 撤销单个文件
git restore .                  # 撤销全部未暂存改动
git clean -fd                  # ⚠️ 删掉新增的未跟踪文件（先看清再执行）
```

### 2.2 提交了，但想撤掉这一次提交（保留改动）

```powershell
git reset --soft HEAD~1        # 撤提交，改动回到暂存区
git reset HEAD~1               # 撤提交，改动回到工作区
```

### 2.3 提交了，想彻底丢掉这一次

```powershell
git reset --hard HEAD~1        # ⚠️ 改动永久丢失
```

### 2.4 回到某个快照（**最常用**）

```powershell
python tools\snapshot.py --diff <tag>   # 先看差异，确认这是你要回到的点
git reset --hard <tag>                  # 回到该快照
```

**如果只是想把某个文件恢复成快照里的样子**（不动其他文件）：

```powershell
git checkout <tag> -- 设计规格
git checkout <tag> -- docs/category-taxonomy.md
```

---

## 3. 危险操作的护栏

| 操作 | 风险 | 护栏 |
|---|---|---|
| `git reset --hard` | 未提交改动永久丢失 | 先 `snapshot` |
| `git clean -fd` | 删除未跟踪文件，不可恢复 | 先 `git clean -nd` 预览 |
| `git push --force` | 覆盖远端历史 | **本仓库禁止**；若必须，先 `git push --force-with-lease` 并告知协作者 |
| `--no-verify` 跳过门禁 | 坏东西进历史 | 仅在明确知道绕的是什么时使用；用后补跑 `gates.cmd all` |

---

## 4. 门禁自己挂了怎么办

门禁是代码，代码会坏。三种情况：

| 现象 | 处理 |
|---|---|
| **误报**（门禁说错了） | ① 先确认真的是误报 ② 在**那一行**加豁免标记：负向断言用 `<!-- allow-negative-assertion: 理由 -->`；绝对路径用 `allow-abs-path` ③ 若是模式本身太宽，改 `spec/negative-assertion-patterns.txt` 并**在 git log 里说明为什么放宽** |
| **真报**（门禁说对了） | **改内容，不要改门禁。** 本项目已两次因"先改工具让它闭嘴"造成后果 |
| **门禁代码有 bug** | 改 `tools/gates.py`，并在提交信息里写明「修的是门禁本身的哪个 bug」 |

**禁止**：为了让自己通过而删除或注释掉检查项。要停用某项，必须：
1. 在 `tools/gates.py` 里把该检查标为 `not_implemented`（不是删掉）
2. 在 `ROADMAP.md` 登记
3. 在提交信息里说明

---

## 5. 门禁现在有什么（**现状**）

| Gate | 状态 | 内容 |
|---|---|---|
| **Gate 0** | ✅ **可跑（11/11）** | `encoding` / **`formula_sync`** / **`card_contract_sync`** / **`ci_coverage_sync`** / `line_endings` / `dod_count` / `negative_assertions` / `secrets` / `abs_paths` / `manifest` / `hook_health` |
| **Gate 1** | ✅ **可跑（7/7）** | `method_card_schema` / `ext_ratio` / `negative_control_refs` / `provenance_components` / `primary_asset_enum` / `impact_class_coverage` / **`card_fixtures`** —— 全部由 `tools/cardcheck.py` 驱动 |
| **Gate 2** | 🟡 **部分可跑** | **`unit_tests`（67 用例，进程内跑）** ✅ / 判据回归 19 条 ⬜ / 逐位可复算 ⬜ / 离线 ⬜ / **`grade_reachable`（Critical 可达 n≥35）** ✅ |

**Gate 2 的 `judge_regression` / `bit_reproducible` / `offline` 目前输出 `[TODO]`，不阻塞提交**——但它们可见，防止被忘记。
>
> **已可跑的两类 Gate 2 检查**：`unit_tests` 在**进程内**跑 `unittest`（**不起子进程**——本环境禁止具名管道，捕获子进程输出会 EPERM）；`grade_reachable` 直接调 `score/core.py` 构造一组 `R_m >= 9.0` 的输入。

**查看**：`python tools\gates.py --list`

### 快照比对（**已修复**）

```
python tools\snapshot.py --list              列出全部快照
python tools\snapshot.py --diff <tag>         与某个快照比对
```

**修复记录**：`--diff` 原先只读 `<tag>:gate-manifest.json`，但该文件被 `.gitignore` 忽略 ⇒ **任何 tag 里都没有它** ⇒ `--diff` 永远返回 1，回退工具在最需要时不可用。
现改为以 **git 树**为准比对（`git diff --name-status <tag> HEAD`），并单独报告工作区未提交的改动；若该 tag 恰好带清单，再额外做一次内容哈希核对。
回归防护见 `tests/test_snapshot_diff.py`。

---

## 6. 三个曾经救过命的检查（**别关掉**）

| 检查 | 它抓到过什么 |
|---|---|
| **`line_endings`** | `gate-manifest.json` 被 Windows 换行翻译成 CRLF —— **这会让产物哈希跨机器不同，直接破坏「逐位可复算」** |
| **`secrets`** | 设计规格 的 NF3 章节里**真的写着一个真实目标 IP:端口** —— 文档在描述"什么不能公开"的时候，自己把那个东西写进去了 |
| **`abs_paths`** | `method-card.schema.json` 的字段说明里含 `外部组件` 绝对路径 —— schema 要公开，这个路径既不通用也泄露内部结构 |

**这三条都不是假想风险，是首次运行就命中的真实缺陷。**
---

## 7. ⚠️ 钩子可能装了却不跑（**必读**）

Git for Windows 执行钩子**必然经过 MSYS 的 `sh`**。在受限环境里 `sh` 可能无法启动
（本项目首次运行即命中：`sh.exe: couldn't create signal pipe, Win32 error 5`），
此时**钩子静默不执行** —— 你会以为有门禁，其实没有。

### 怎么知道自己有没有被保护

```powershell
python tools\gates.py --check hook_health
```

| 输出 | 含义 | 怎么办 |
|---|---|---|
| `钩子可用（sh: ...）` | 提交时门禁会自动跑 | 正常用 `git commit` 即可 |
| `钩子不可用（必须用提交包装器）` | **钩子不会执行** | **必须**改用下面的包装器 |

### 不依赖钩子的强制路径（**任何环境都可用**）

```powershell
# 方式一：命令行包装器（推荐）
.\gates.cmd commit -m "feat(methods): 新增 T01 的 12 张卡"

# 方式二：直接调
python tools\gate_commit.py -m "feat(methods): 新增 T01 的 12 张卡"

# 让包装器跑更全的检查
python tools\gate_commit.py -m "..." --gate all
```

包装器的行为：**先跑门禁，不通过就不提交**；通过才 `git add -A` 并提交。
它用 `--no-verify` 提交，避免在钩子能跑的环境里跑第二遍。

### 紧急绕过（**会留痕**）

```powershell
python tools\gate_commit.py -m "..." --skip-gate
```

提交信息里会被自动加上一行 `[gate-skipped] 本次提交绕过了门禁（--skip-gate）`。
**绕过不是免费的**——事后 `git log --grep gate-skipped` 就能查出全部绕过记录。

### 给 CI 的建议

Linux/macOS 上 `sh` 正常，钩子可用；CI 里建议**两者都配**：
`make ci` 作为主门禁，钩子作为本地兜底。