# ============================================================
#  Quality gate entry point (PowerShell)
#  All human-readable output comes from Python.
# ============================================================
param(
  [ValidateSet('0','1','2','all','list','snapshot')]
  [string]$Gate = '0'
)
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'

switch ($Gate) {
  'list'     { python tools/gates.py --list }
  'snapshot' { python tools/snapshot.py }
  default    { python tools/gates.py --gate $Gate }
}
exit $LASTEXITCODE