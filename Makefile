# 本 Makefile 供 CI 与 Linux/macOS 使用。
# Windows 无 make：请用 gates.cmd / gates.ps1 / 直接 python tools/gates.py。
# 目标名与 docs/technical-design.md §3.5 的 CLI 映射一致。

PY ?= python
export PYTHONIOENCODING := utf-8

.PHONY: help gates gates0 gatesall list snapshot test test-scoring sync ci

help:
	@echo "make gates0     Gate 0 入库检查（当前可跑）"
	@echo "make gatesall   全部 Gate（含未实现的占位）"
	@echo "make list       列出全部检查"
	@echo "make snapshot   打快照（tag + 清单哈希）"
	@echo "make test       跑测试（unittest）"
	@echo "make sync       规范 vs 实现 对账"
	@echo "make ci         发布门禁（等同 make gatesall）"

gates0:
	$(PY) tools/gates.py --gate 0

gatesall:
	$(PY) tools/gates.py --gate all

gates: gates0

list:
	$(PY) tools/gates.py --list

snapshot:
	$(PY) tools/snapshot.py

# 依 docs/docs/README.md.md B4（纯标准库）：测试框架是标准库 unittest，不引入 pytest。
test:
	$(PY) -m unittest discover -s tests -t . -v

# 只跑那些把 spec/scoring.md 的断言变成可执行事实的用例
test-scoring:
	$(PY) -m unittest tests.test_score_core -v

# 规范 ↔ 实现 对账（不跑测试，只比常数）
sync:
	$(PY) tools/gates.py --check formula_sync

ci: gatesall