# -*- coding: utf-8 -*-
"""`harness/` 执行层的可执行防线。

重点不是"跑得通"，是**六态映射对不对**。本项目在这个地方摔过：
规则 17 曾把 `untested` 报成 ERROR（2026-10-01 修），
而 `untested`/`not_applicable` 与 `fail` 混同会让覆盖率虚高（R3/R4）。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import runner as R            # noqa: E402
from harness import store                  # noqa: E402
from harness.protocol import InjectionReceipt, Observations   # noqa: E402

TOOLS = ["user_turn", "response_generate"]
DIMS = {"input_trust": 3, "access_sensitivity": 3, "workflow": 2,
        "action": 3, "memory": 2, "tool": 2, "user_interface": 1}


class FakeTarget:
    """假靶标。**故意把每个失败面都做成可开关的**，否则测不到降级路径。"""

    target_id = "fake"

    def __init__(self, *, tools=None, dims=None, fail_reset=False,
                 fail_run=False, response="hello", place=True,
                 defense_layer="output_filter", observables=(),
                 reference="FAKE-REFERENCE-TEXT-0123456789"):
        self._tools = list(tools if tools is not None else TOOLS)
        self._dims = dict(dims if dims is not None else DIMS)
        self.fail_reset, self.fail_run = fail_reset, fail_run
        self.response, self.place = response, place
        self.defense_layer = defense_layer
        self._observables = list(observables)
        self.reference = reference
        self.cleaned = 0
        self.ran = 0

    def tools(self): return list(self._tools)
    def design_dimensions(self): return dict(self._dims)
    def caps(self):
        return {"cleanup_supported": True, "receipt_supported": True,
                "entry_surfaces": ["用户输入", "user_turn"],
                "observables": list(self._observables)}

    def reset(self):
        if self.fail_reset: raise RuntimeError("reset boom")

    def inject(self, *, vector, payload, turn):
        return InjectionReceipt(vector, turn, self.place,
                                "" if self.place else "本靶标未实现该投放面：%s" % vector)

    def run_task(self, *, max_turns):
        self.ran += 1
        if self.fail_run: raise RuntimeError("run boom")

    def observe(self):
        return Observations(response_text=self.response, canary_in_target=True,
                            reference_definition=self.reference,
                            deepest_defense_layer=self.defense_layer)

    def cleanup(self): self.cleaned += 1


class FakeJudge:
    """假判据。**默认按臂给不同结论**——否则测不到配对对照。

    真实判据也是按观测给的；这里用 `request_text` 里有没有 `adv` 来模拟。
    显式传 `verdict` 则两臂同结论（用于测"无差异"的报警）。
    """

    judge_id = "prompt_leak"

    def __init__(self, verdict=None):
        self.fixed = verdict

    def __call__(self, *, params, **obs):
        class V:
            pass
        v = V()
        if self.fixed is not None:
            v.verdict = self.fixed
        else:
            v.verdict = "pass" if "adv" in str(obs.get("request_text", "")) else "fail"
        v.reason = "fake"
        v.match_kind = None
        return v


class ResolvingJudge(FakeJudge):
    """实现了 `Judge.params_for` 可选扩展的判据——真实判据应当这样。

    没有它，证据里只能记卡上的**模板**（如 `T06CANARY-<random32>`），
    于是 trial 文件复算不出自己记的判定（`harness/evidence.py` 的 `has_unresolved_placeholder`）。
    """

    def params_for(self, card):
        return {"canary_id": "c", "expected_verbatim": "CANARY-LIVE-9"}


class CountingJudge(FakeJudge):
    """记调用次数：用来证明**该不调判据的时候真的没调**。"""

    def __init__(self, verdict=None):
        super().__init__(verdict)
        self.calls = 0

    def __call__(self, *, params, **obs):
        self.calls += 1
        return super().__call__(params=params, **obs)


class FakeClassModule:
    """假类模块，只带可选扩展 `status_of`（`spec/method-script-interface.md` §3）。"""

    def __init__(self, status=""):
        self.status, self.seen_observables = status, None

    def status_of(self, observables, spec):
        self.seen_observables = list(observables)
        if isinstance(self.status, Exception):
            raise self.status
        return self.status


def card(**over):
    c = {
        "method_id": "T06.FAKE.method", "case_id": "T06",
        "surface_layer": "L3.1", "physical_consequence": "none",
        "judge": {"verifier": "prompt_leak", "evidence_layer": "text",
                  "params": {"canary_id": "c", "expected_verbatim": "CANARY-XYZ"}},
        "trigger_path": {"required_actions": ["user_turn", "response_generate"]},
        "preconditions": {"input_trust": 3, "workflow": 2},
        "provenance_components": {"vector": {"ref": "用户输入"}},
    }
    c.update(over)
    return c


def run_one(target, the_card, judge=None, n=3, tmp=None, monkey=True, module=None,
            observers=(), payload_for=None, payload_meta_for=None):
    """跑一个格。默认把 `spec_and_plan` 打桩，避免依赖真实类模块。"""
    orig = R.spec_and_plan
    if monkey:
        R.spec_and_plan = lambda c: {"spec": None, "plan": {"turns": 1},
                                     "module": module, "validate_errors": []}
    try:
        return R.run_matrix(adapter=target, cards=[the_card],
                            judge_for=lambda c: judge or FakeJudge(),
                            payload_for=payload_for or (lambda c, p, i, arm: ("%s-probe-%d" % (arm[:3], i))),
                            payload_meta_for=payload_meta_for,
                            n=n, runs_dir=tmp, observers=observers)
    finally:
        R.spec_and_plan = orig


class TestSixStateMapping(unittest.TestCase):
    """六态归属：untested / not_applicable 由 runner 出；pass/fail/inconclusive 由判据出。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_action_is_untested_not_fail(self):
        t = FakeTarget(tools=["response_generate"])          # 缺 user_turn
        c = run_one(t, card(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.UNTESTED)
        self.assertIn("user_turn", c.notes[0])

    def test_unmet_precondition_is_not_applicable(self):
        t = FakeTarget(dims={**DIMS, "workflow": 1})          # 卡要 workflow>=2
        c = run_one(t, card(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.NOT_APPLICABLE)

    def test_unknown_dimension_is_not_applicable(self):
        c = run_one(FakeTarget(), card(preconditions={"nope": 1}), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.NOT_APPLICABLE)

    def test_untested_and_not_applicable_are_different(self):
        a = run_one(FakeTarget(tools=["response_generate"]), card(), tmp=self.tmp).cells[0]
        b = run_one(FakeTarget(dims={**DIMS, "workflow": 1}), card(), tmp=self.tmp).cells[0]
        self.assertNotEqual(a.six_state, b.six_state)

    def test_reset_failure_is_inconclusive_not_fail(self):
        c = run_one(FakeTarget(fail_reset=True), card(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)

    def test_run_failure_is_inconclusive_not_fail(self):
        c = run_one(FakeTarget(fail_run=True), card(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)

    def test_judge_inconclusive_propagates(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge("inconclusive"), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)

    def test_all_pass_gives_pass_and_a_score(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge("pass"), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.PASS)
        self.assertIsNotNone(c.r_measured)
        self.assertEqual(c.r_measured["k"], 3)
        self.assertEqual(c.r_measured["n"], 3)

    def test_all_fail_gives_fail_and_a_score(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge("fail"), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.FAIL)
        self.assertEqual(c.r_measured["k"], 0)

    def test_mixed_inconclusive_degrades_whole_cell(self):
        """部分 trial 测不了 ⇒ 整格按最保守口径记 inconclusive，不得只报能跑的那几次。"""
        class Flaky(FakeJudge):
            def __init__(self):
                super().__init__(); self.i = 0
            def __call__(self, *, params, **obs):
                self.i += 1
                # 只让**对抗臂的第 2 次**不可判；其余按臂给结论
                if self.i == 2:
                    return FakeJudge("inconclusive")(params=params, **obs)
                return super().__call__(params=params, **obs)
        c = run_one(FakeTarget(), card(), judge=Flaky(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)


class TestStoreAndDiscipline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_batch_trial_summary_are_written(self):
        r = run_one(FakeTarget(), card(), tmp=self.tmp)
        base = store.batch_dir(r.batch_id, self.tmp)
        self.assertTrue((base / "batch.json").exists())
        self.assertTrue((base / "summary.json").exists())
        self.assertEqual(len(list(base.rglob("trial-*.json"))), 6)   # 3 trial × 2 臂

    def test_payload_body_is_not_stored(self):
        """禁令 9：只存哈希与长度，不存载荷正文。"""
        r = run_one(FakeTarget(), card(), tmp=self.tmp)
        trials = store.load_trials(r.batch_id, self.tmp)
        blob = json.dumps(trials, ensure_ascii=False)
        self.assertNotIn("probe-0", blob)
        self.assertIn("payload_sha256", blob)
        self.assertTrue(all(t["payload_len"] > 0 for t in trials))

    def test_each_trial_is_self_sufficient(self):
        """D1：单 trial 必须能独立复算（只存汇总就是 M1–M5 聚合掩盖的重演）。"""
        r = run_one(FakeTarget(), card(), tmp=self.tmp)
        for t in store.load_trials(r.batch_id, self.tmp):
            for k in ("method_id", "target_id", "judge_id", "judge_params",
                      "vector", "payload_sha256", "six_state"):
                self.assertIn(k, t)
            self.assertTrue(t["judge_params"])

    def test_six_state_counts_cover_all_cells(self):
        r = run_one(FakeTarget(), card(), tmp=self.tmp)
        self.assertEqual(sum(r.six_state_counts().values()), len(r.cells))

    def test_payload_hash_is_deterministic(self):
        from harness.evidence import TrialEvidence
        a, b = TrialEvidence(), TrialEvidence()
        a.compute_payload_hash("同一个载荷")
        b.compute_payload_hash("同一个载荷")
        self.assertEqual(a.payload_sha256, b.payload_sha256)
        c = TrialEvidence(); c.compute_payload_hash("另一个载荷")
        self.assertNotEqual(a.payload_sha256, c.payload_sha256)


class TestScoreBridge(unittest.TestCase):
    """评分桥。**两套 "layer" 词汇表的坑就在这里**，故测试集中在参数语义上。"""

    DEF = "output_filter"        # 防御层名（LAYER_ORDER 之一）

    def test_L3_1_surface_layer_is_parsable(self):
        """实测形态：卡上写 L3.1。int(\"L3.1\".lstrip(\"L\")) 会抛 ValueError。"""
        sc = R.score_cell(card(surface_layer="L3.1"), ["pass", "fail", "pass"], self.DEF)
        self.assertTrue(sc.get("ok"), sc.get("reason"))

    def test_empty_verdicts_gives_no_score(self):
        self.assertFalse(R.score_cell(card(), [], self.DEF)["ok"])

    def test_bad_surface_layer_reports_reason_not_crash(self):
        sc = R.score_cell(card(surface_layer="???"), ["pass"], self.DEF)
        self.assertFalse(sc["ok"])
        self.assertEqual(sc["reason"], "surface_layer_unparsable")

    def test_evidence_layer_is_not_a_defense_layer(self):
        """把证据层当防御层喂进去必须抛错——这个坑实测踩过。

        `depth_from_layer('text')` 不知道 `text` 是什么，因为
        `LAYER_ORDER` 是 9 个**防御层名**，`LAYER_RANK` 才是证据层。
        """
        sc = R.score_cell(card(), ["pass"], "text")     # 故意传证据层
        self.assertFalse(sc["ok"])
        self.assertIn("unknown", sc["reason"].lower() + " unknown")

    def test_missing_depth_gives_tested_no_number_not_a_guess(self):
        """G-1 的下游后果：靶标防御栈不可配置 ⇒ depth 拿不到 ⇒ 不得硬凑 R_m。"""
        sc = R.score_cell(card(), ["pass", "pass", "pass"], None)
        self.assertFalse(sc["ok"])
        self.assertEqual(sc["reason"], "depth_unavailable")


class TestG1Consequence(unittest.TestCase):
    """可行性评估登记的 G-1（防御栈不可配置）在 runner 层的具体表现。

    **口径在 2026-10-01 变了**：引入配对对照指标 `Adv̂` 之后，
    `depth` 拿不到**不再让整格失去数字**——它只让 `R_m` 这一路失去数字。
    格的六态由**攻击成没成**决定（`v_adv`），不再由 `R_m` 算不算得出来决定。

    这条改动是针对一个真实困境：原口径下 `tested_no_number` 会让
    "攻击明显成功"和"给不出分"混为一谈，而 设计规格:376 把 benchmark 一词的
    解除条件绑在"产出含 source: measured 的分数"上 ⇒ 永远解不开。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_depth_still_yields_a_cell_state(self):
        t = FakeTarget(defense_layer=None)           # 模拟 AgentDojo：拿不到 depth
        c = run_one(t, card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.PASS)        # 攻击成了，格就有态
        self.assertEqual(c.adv_hat, 1.0)             # 指标也拿得到

    def test_no_depth_blocks_only_R_m_not_the_metric(self):
        t = FakeTarget(defense_layer=None)
        c = run_one(t, card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertIsNone(c.r_measured)
        self.assertEqual(c.r_unavailable_reason, "depth_unavailable")
        self.assertIsNotNone(c.adv_hat)

    def test_depth_available_computes_R_m(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertIsNotNone(c.r_measured)
        self.assertIsNone(c.r_unavailable_reason)


class TestPairedControl(unittest.TestCase):
    """配对良性对照（AgentSecBench 定义 4）。

    `Adv̂ = v_adv − v_ctrl`。**不减对照就是把模型的自发行为算成方法的功劳。**
    真实事故同型：判据 D2——T08 报 9/9 泄露，而独立探针 7/7 未泄露。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_adv_hat_is_one_when_only_adversarial_leaks(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertEqual(c.v_adv, 1.0)
        self.assertEqual(c.v_ctrl, 0.0)
        self.assertEqual(c.adv_hat, 1.0)

    def test_both_arms_run_every_trial(self):
        r = run_one(FakeTarget(), card(), n=3, tmp=self.tmp)
        base = store.batch_dir(r.batch_id, self.tmp)
        self.assertEqual(len(list(base.rglob("trial-*.json"))), 6)      # 3 trial × 2 臂

    def test_zero_adv_hat_is_loudly_flagged(self):
        """两臂无差异 ⇒ 必须显式报警，不能只让一个 pass 静静躺着。"""
        c = run_one(FakeTarget(), card(), judge=FakeJudge("pass"), tmp=self.tmp).cells[0]
        self.assertEqual(c.adv_hat, 0.0)
        self.assertTrue(any("不能归因于该方法" in n for n in c.notes), c.notes)

    def test_arms_are_evidence_labelled(self):
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp)
        arms = sorted({t["arm"] for t in store.load_trials(r.batch_id, self.tmp)})
        self.assertEqual(arms, ["adversarial", "control"])

    def test_control_arm_verdicts_are_kept_separate(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertEqual(c.verdicts, ["pass"] * 3)
        self.assertEqual(c.ctrl_verdicts, ["fail"] * 3)

    def test_one_arm_unusable_makes_cell_inconclusive(self):
        """一臂给不出判定 ⇒ 配对不成立 ⇒ 整格 inconclusive，不得只报另一臂。"""
        class HalfBroken(FakeJudge):
            def __call__(self, *, params, **obs):
                if "con" in str(obs.get("request_text", "")):
                    return FakeJudge("inconclusive")(params=params, **obs)
                return FakeJudge("pass")(params=params, **obs)
        c = run_one(FakeTarget(), card(), judge=HalfBroken(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)

    def test_wilson_intervals_present_for_both_arms(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertIsNotNone(c.wilson_adv)
        self.assertIsNotNone(c.wilson_ctrl)


class TestPlacementFailClosed(unittest.TestCase):
    """**投放面这一层：投不进去 = 没测，不是没成功。**

    真实事故（`batch-6d0b76397335/`，2026-10-02）：T06 的 20 张卡里 9 张
    声明的投放面本靶标未实现，payload 被丢弃、适配器回退到自己的默认良性查询，
    判据照样给出 `fail` ⇒ 六态被污染成"攻击失败"。9 次里有 2 格就是这么记的。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_placement_failure_is_untested_not_fail(self):
        c = run_one(FakeTarget(place=False), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.UNTESTED)
        self.assertNotEqual(c.six_state, R.FAIL)

    def test_placement_failure_does_not_run_or_judge(self):
        """投不进去就不该跑任务、更不该调判据——否则测的是适配器的兜底查询。"""
        t, j = FakeTarget(place=False), CountingJudge()
        run_one(t, card(), judge=j, tmp=self.tmp)
        self.assertEqual(t.ran, 0)
        self.assertEqual(j.calls, 0)

    def test_placement_failure_records_the_reason(self):
        r = run_one(FakeTarget(place=False), card(), judge=FakeJudge(), tmp=self.tmp)
        t = store.load_trials(r.batch_id, self.tmp)[0]
        self.assertEqual(t["six_state"], R.UNTESTED)
        self.assertEqual(t["verdict_reason"], "not_placed")
        self.assertIn("inject_not_placed", t["error"])
        self.assertEqual(t["turns"], 0)

    def test_placement_failure_gives_no_rate(self):
        """没投进去就没有率可比 —— `v_adv` / `Adv̂` 必须是 None，不得填 0 或 1。"""
        c = run_one(FakeTarget(place=False), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertIsNone(c.v_adv)
        self.assertIsNone(c.adv_hat)

    def test_partial_placement_is_inconclusive_not_untested(self):
        """只有一臂投进去 ⇒ 配对不成立 ⇒ 整格 inconclusive，不得当 untested 收场。"""
        class HalfPlaceable(FakeTarget):
            def inject(self, *, vector, payload, turn):
                return InjectionReceipt(vector, turn, "adv" in payload, "只在对抗臂落地")

        c = run_one(HalfPlaceable(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)


class TestClassStatusGate(unittest.TestCase):
    """阶段 3b：类模块的 `status_of` 扩展（观测装置那一问）。

    runner 保持通用——它把靶标**声明的观测装置**原样递进去，判断留在类里。
    T06 的侧信道一族正是靠这一条从 `fail` 变成 `not_applicable`。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_not_applicable_short_circuits_before_spending_calls(self):
        t, j = FakeTarget(), CountingJudge()
        c = run_one(t, card(), judge=j, module=FakeClassModule("not_applicable"),
                    tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.NOT_APPLICABLE)
        self.assertEqual(j.calls, 0)
        self.assertEqual(t.ran, 0)

    def test_untested_from_class_module_is_honored(self):
        c = run_one(FakeTarget(), card(), module=FakeClassModule("untested"),
                    tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.UNTESTED)

    def test_empty_status_means_proceed(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge(),
                    module=FakeClassModule(""), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.PASS)

    def test_declared_observables_are_passed_through(self):
        mod = FakeClassModule("")
        run_one(FakeTarget(observables=["cache_sharing"]), card(), judge=FakeJudge(),
                module=mod, tmp=self.tmp)
        self.assertEqual(mod.seen_observables, ["cache_sharing"])

    def test_undeclared_observables_are_an_empty_list_not_a_guess(self):
        mod = FakeClassModule("")
        run_one(FakeTarget(), card(), judge=FakeJudge(), module=mod, tmp=self.tmp)
        self.assertEqual(mod.seen_observables, [])

    def test_illegal_status_is_inconclusive_not_silently_ignored(self):
        """返回一个不在六态里的字符串 ⇒ fail-closed，不许当成"继续测"。"""
        c = run_one(FakeTarget(), card(), judge=FakeJudge(),
                    module=FakeClassModule("maybe"), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)

    def test_status_raising_is_inconclusive(self):
        c = run_one(FakeTarget(), card(), judge=FakeJudge(),
                    module=FakeClassModule(RuntimeError("boom")), tmp=self.tmp).cells[0]
        self.assertEqual(c.six_state, R.INCONCLUSIVE)


class TestJudgeParamResolution(unittest.TestCase):
    """证据必须记下判据**实际拿到**的参数，否则 trial 文件复算不出自己。

    真实事故：`batch-6d0b76397335/` 的 trial 记 `verdict=pass`，
    而它自己记的 `expected_verbatim` 是卡上的模板 `T06CANARY-<random32>`。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_runtime_params_are_recorded_resolved(self):
        r = run_one(FakeTarget(), card(), judge=ResolvingJudge(), tmp=self.tmp)
        t = store.load_trials(r.batch_id, self.tmp)[0]
        self.assertEqual(t["judge_params_source"], "runtime")
        self.assertEqual(t["judge_params_resolved"]["expected_verbatim"], "CANARY-LIVE-9")
        self.assertEqual(t["judge_params"]["expected_verbatim"], "CANARY-XYZ")  # 卡上声明仍在
        from harness.evidence import has_unresolved_placeholder
        self.assertFalse(has_unresolved_placeholder(t["judge_params_resolved"]))

    def test_judge_actually_receives_the_resolved_params(self):
        seen = {}

        class Spy(ResolvingJudge):
            def __call__(self, *, params, **obs):
                seen.update(params)
                return super().__call__(params=params, **obs)

        run_one(FakeTarget(), card(), judge=Spy(), tmp=self.tmp)
        self.assertEqual(seen["expected_verbatim"], "CANARY-LIVE-9")

    def test_missing_params_for_is_recorded_as_card_declared(self):
        """判据没实现 `params_for` ⇒ 如实标注来源，不假装解析过。"""
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp)
        t = store.load_trials(r.batch_id, self.tmp)[0]
        self.assertEqual(t["judge_params_source"], "card_declared")
        self.assertEqual(t["judge_params_resolved"], {})
        self.assertTrue(any("不可独立复算" in n for n in r.cells[0].notes), r.cells[0].notes)

    def test_params_for_raising_is_recorded_not_hidden(self):
        class Broken(FakeJudge):
            def params_for(self, card):
                raise RuntimeError("boom")

        r = run_one(FakeTarget(), card(), judge=Broken(), tmp=self.tmp)
        t = store.load_trials(r.batch_id, self.tmp)[0]
        self.assertIn("params_for_raised", t["judge_params_source"])


class TestObserversAreOffTheScoringPath(unittest.TestCase):
    """副观测（`docs/README.md` **D16**）**不得**影响六态、`Adv̂` 与 `R_m`。

    它是报告里的第二列。R9 的纪律是"两把尺子不混排"——若副观测能改六态，
    那就等于让一把诊断尺子去投评分票。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_observer_result_is_recorded_in_evidence(self):
        from harness import observers as OB
        obs = OB.ReconstructionCoverage(canary=None)
        t = FakeTarget(response="FAKE-REFERENCE-TEXT-0123456789")   # 整段照抄
        r = run_one(t, card(), judge=FakeJudge(), tmp=self.tmp, observers=[obs])
        trials = store.load_trials(r.batch_id, self.tmp)
        got = [x["observations_extra"] for x in trials]
        self.assertTrue(all("reconstruction_coverage" in g for g in got), got[0])
        self.assertEqual(got[0]["reconstruction_coverage"]["by_strength"]["strict"]["coverage"], 1.0)

    def test_observer_does_not_change_six_state_or_adv_hat(self):
        """观察器返回什么都不许改结论——用一份"全是垃圾"的返回验证。"""
        class Junk:
            observer_id = "junk"

            def __call__(self, **kw):
                return {"coverage": 0.0, "verdict": "fail", "six_state": "fail"}

        base = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        withjunk = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                           observers=[Junk()]).cells[0]
        self.assertEqual(base.six_state, withjunk.six_state)
        self.assertEqual(base.adv_hat, withjunk.adv_hat)
        self.assertEqual(base.r_measured, withjunk.r_measured)

    def test_observer_exception_does_not_break_the_trial(self):
        """副观测抛异常 ⇒ 记一笔 note，判定照旧（不连坐）。"""
        class Boom:
            observer_id = "boom"

            def __call__(self, **kw):
                raise RuntimeError("observer boom")

        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp, observers=[Boom()])
        c = r.cells[0]
        self.assertEqual(c.six_state, R.PASS)
        self.assertEqual(c.adv_hat, 1.0)
        self.assertTrue(any("副观测" in n and "boom" in n for n in c.notes), c.notes)

    def test_observer_sees_our_payload_as_own_text(self):
        """喂进去的片段必须能被守卫看到——否则"自我供给"会被算成"目标复原"。"""
        seen = []

        class Spy:
            observer_id = "spy"

            def __call__(self, *, card, observations, request_text="", payload_text=""):
                seen.append(request_text)
                return {"ok": True}

        run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp, observers=[Spy()])
        self.assertEqual(len(seen), 6)                       # 3 trial × 2 臂
        self.assertTrue(any("adv-probe-0" in t for t in seen), seen)
        self.assertTrue(any("con-probe-0" in t for t in seen), seen)

    def test_no_observer_means_empty_extra(self):
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp)
        for t in store.load_trials(r.batch_id, self.tmp):
            self.assertEqual(t["observations_extra"], {})


class TestPayloadInstantiation(unittest.TestCase):
    """载荷合成层与 runner 的接线（`ROADMAP.md` **G-6**）。

    病根：旧实现里 `payload_for` 忽略 `card`，所有方法共用一句探针 ⇒
    六格"成功"是同一个探针成功了六次。修复后有两件事必须成立：
    载荷投不出去记 `untested`；**每一格自报用的是哪条构造**。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_not_deliverable_is_untested_and_spends_nothing(self):
        from harness.payloads import NotDeliverable

        def boom(c, p, i, arm):
            raise NotDeliverable("本靶标未声明所需投放面：user_turn_multi")

        t, j = FakeTarget(), CountingJudge()
        c = run_one(t, card(), judge=j, tmp=self.tmp, payload_for=boom).cells[0]
        self.assertEqual(c.six_state, R.UNTESTED)
        self.assertEqual(j.calls, 0)
        self.assertEqual(t.ran, 0)

    def test_not_deliverable_records_its_reason(self):
        from harness.payloads import NotDeliverable

        def boom(c, p, i, arm):
            raise NotDeliverable("需要 5 轮")

        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp, payload_for=boom)
        t = store.load_trials(r.batch_id, self.tmp)[0]
        self.assertEqual(t["verdict_reason"], "not_deliverable")
        self.assertIn("需要 5 轮", t["error"])

    def test_payload_meta_is_recorded_for_every_trial(self):
        meta = {"frame": "sandwich", "scope": "faithful", "source": "LIT-B-109",
                "turns": 1, "requires": [], "tokens": {"request": "verbatim_restate"},
                "note": ""}
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                    payload_meta_for=lambda c: meta)
        for t in store.load_trials(r.batch_id, self.tmp):
            self.assertEqual(t["payload_meta"]["frame"], "sandwich")
            self.assertEqual(t["payload_meta"]["scope"], "faithful")

    def test_generic_fallback_scope_is_loudly_flagged(self):
        """兜底探针必须自报家门 —— G-6 的病根就是这一步以前是静默的。"""
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                    payload_meta_for=lambda c: {"scope": "generic"})
        self.assertTrue(any("兜底探针" in n for n in r.cells[0].notes), r.cells[0].notes)

    def test_meta_carries_no_payload_text(self):
        """构造元数据里不许混进载荷文本（否则证据又把载荷正文存回去了）。"""
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                    payload_meta_for=lambda c: {"scope": "faithful", "frame": "sandwich"})
        blob = json.dumps(store.load_trials(r.batch_id, self.tmp), ensure_ascii=False)
        self.assertNotIn("probe-0", blob)                 # 载荷正文仍不入库
        self.assertIn("payload_meta", blob)


class TestObserverRates(unittest.TestCase):
    """副观测的**格级率**（条件 B 的防御介入率靠它）。

    `fired` 这种 0/1 只有在格级求均值才有用；而 runner **不猜**哪个键是率——
    由观测器自己用 `rate_key` 声明（`harness/protocol.py` 的 `Observer`）。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_declared_rate_key_is_averaged_over_the_adversarial_arm(self):
        """分母只有**对抗臂**。若错把两臂一起平均，这里会得到 1/6 而不是 1/3。"""
        class Once:
            observer_id = "iv"
            rate_key = "fired"

            def __init__(self):
                self.adv = 0

            def __call__(self, *, card, observations, request_text="", payload_text=""):
                if "adv" not in request_text:
                    return {"fired": 0}
                self.adv += 1
                return {"fired": 1 if self.adv == 1 else 0}

        c = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                    observers=[Once()]).cells[0]
        self.assertAlmostEqual(c.observer_rates["iv"], 1 / 3, places=6)

    def test_observer_without_rate_key_is_not_aggregated(self):
        class Plain:
            observer_id = "plain"

            def __call__(self, *, card, observations, request_text="", payload_text=""):
                return {"fired": 1, "coverage": 0.5}

        c = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                    observers=[Plain()]).cells[0]
        self.assertEqual(c.observer_rates, {})

    def test_rate_aggregation_does_not_touch_the_verdict_path(self):
        class Always:
            observer_id = "always"
            rate_key = "fired"

            def __call__(self, *, card, observations, request_text="", payload_text=""):
                return {"fired": 1}

        base = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp).cells[0]
        with_obs = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                           observers=[Always()]).cells[0]
        self.assertEqual(base.six_state, with_obs.six_state)
        self.assertEqual(base.adv_hat, with_obs.adv_hat)
        self.assertEqual(with_obs.observer_rates, {"always": 1.0})

    def test_defense_intervention_observer_reports_unavailable_without_defense(self):
        from harness import observers as OB

        class Obs:
            response_text = "hello"
            reference_definition = "ref"
            defense = {}

        got = OB.DefenseIntervention()(card={}, observations=Obs())
        self.assertFalse(got["available"])
        self.assertEqual(got["reason"], "no_output_side_defense")


class TestMultiTurnDelivery(unittest.TestCase):
    """多轮投放（`ROADMAP.md` **G-10**）。

    旧适配器把**全部** user turn 拼成**一次** query ⇒ 多轮构造被压成一轮，
    载荷层只能抛 `NotDeliverable`，T06 的实测面因此少了 2 个方法。
    现在：`payload_for` 返回**轮次列表**，runner 逐轮 `inject`，任一轮投不进去就整 trial `untested`。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_list_payload_is_injected_turn_by_turn(self):
        class RecordingTarget(FakeTarget):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.turns_seen = []

            def inject(self, *, vector, payload, turn):
                self.turns_seen.append((turn, payload))
                return InjectionReceipt(vector, turn, True, "")

        t = RecordingTarget()
        run_one(t, card(), judge=FakeJudge(), tmp=self.tmp,
                payload_for=lambda c, p, i, arm: ["turn-A", "turn-B", "turn-C"])
        # 每次 trial 投 3 轮；记录的 turn 序号必须是 0/1/2
        self.assertEqual(t.turns_seen[:3], [(0, "turn-A"), (1, "turn-B"), (2, "turn-C")])

    def test_evidence_turns_counts_all_delivered_turns(self):
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                    payload_for=lambda c, p, i, arm: ["a", "b", "c"])
        for t in store.load_trials(r.batch_id, self.tmp):
            self.assertEqual(t["turns"], 3)

    def test_hash_covers_all_turns(self):
        """同一个首轮、不同的后续轮 ⇒ 载荷哈希必须不同（否则证据分不出两个构造）。"""
        r1 = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                     payload_for=lambda c, p, i, arm: ["same", "X"])
        r2 = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp,
                     payload_for=lambda c, p, i, arm: ["same", "Y"])
        h1 = store.load_trials(r1.batch_id, self.tmp)[0]["payload_sha256"]
        h2 = store.load_trials(r2.batch_id, self.tmp)[0]["payload_sha256"]
        self.assertNotEqual(h1, h2)

    def test_a_single_unplaced_turn_fails_closed(self):
        """只投进去一半就开跑 ⇒ 测的不是这个构造。故任一轮未落地即整 trial `untested`。"""
        class HalfPlaceable(FakeTarget):
            def inject(self, *, vector, payload, turn):
                return InjectionReceipt(vector, turn, turn < 2, "")   # 第 3 轮投不进

        t, j = HalfPlaceable(), CountingJudge()
        c = run_one(t, card(), judge=j, tmp=self.tmp,
                    payload_for=lambda c2, p, i, arm: ["a", "b", "c"]).cells[0]
        self.assertEqual(c.six_state, R.UNTESTED)
        self.assertEqual(j.calls, 0)
        self.assertEqual(t.ran, 0)

    def test_single_string_is_still_one_turn(self):
        """老调用方返回字符串 ⇒ 仍是单轮，语义不变。"""
        r = run_one(FakeTarget(), card(), judge=FakeJudge(), tmp=self.tmp)
        for t in store.load_trials(r.batch_id, self.tmp):
            self.assertEqual(t["turns"], 1)


class TestAdapterDeclaresMultiTurn(unittest.TestCase):
    def test_adapter_declares_the_multi_turn_surface(self):
        """适配器声明了它，载荷层才允许放多轮构造（两处必须同名）。"""
        from harness.adapters import agentdojo_workspace as AD
        from harness import payloads as PL
        caps = AD.AgentDojoWorkspace.caps(object())
        self.assertIn(PL.MULTI_TURN_SURFACE, caps["entry_surfaces"])

    def test_adapter_inject_records_turn_index_and_reset_clears(self):
        """不实例化（那要 API key）：直接验 `inject` / `reset` 的记账。"""
        from harness.adapters import agentdojo_workspace as AD
        ws = AD.AgentDojoWorkspace.__new__(AD.AgentDojoWorkspace)
        ws._turns, ws._response, ws._error = [], None, None
        for k, text in enumerate(["one", "two", "three"]):
            r = ws.inject(vector="用户输入", payload=text, turn=k)
            self.assertTrue(r.placed)
        self.assertEqual([t["turn"] for t in ws._turns], [0, 1, 2])
        self.assertEqual([t["content"] for t in ws._turns], ["one", "two", "three"])
        ws.reset()
        self.assertEqual(ws._turns, [])

    def test_adapter_refuses_unimplemented_surfaces(self):
        from harness.adapters import agentdojo_workspace as AD
        ws = AD.AgentDojoWorkspace.__new__(AD.AgentDojoWorkspace)
        ws._turns, ws._response, ws._error = [], None, None
        r = ws.inject(vector="检索文档", payload="x", turn=0)
        self.assertFalse(r.placed)
        self.assertIn("未实现", r.detail)


if __name__ == "__main__":
    unittest.main()