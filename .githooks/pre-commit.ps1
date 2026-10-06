# Windows 原生 pre-commit（当 git 未走 sh 时使用）
# 用法： 把本文件内容复制到 .git/hooks/pre-commit（无扩展名）亦可，
#        但推荐用 .githooks/pre-commit（POSIX 版，Git for Windows 自带 sh）。
$ErrorActionPreference = 'Continue'
Set-Location (git rev-parse --show-toplevel)
$env:PYTHONIOENCODING = 'utf-8'
python tools/gates.py --gate 0
exit $LASTEXITCODE