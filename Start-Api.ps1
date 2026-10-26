param([int]$Port=8000,[switch]$Reload)
$ErrorActionPreference="Stop"
$python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Create .venv and install requirements-dev.txt as described in README.md." }
$arguments=@("-m","uvicorn","app.main:app","--port",$Port)
if ($Reload) { $arguments+="--reload" }
Push-Location $PSScriptRoot
try { & $python @arguments }
finally { Pop-Location }

