$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.runtime\python.exe'
if (!(Test-Path -LiteralPath $python)) { $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
if (!(Test-Path -LiteralPath $python)) { throw 'Create .venv and install requirements first.' }
& $python 'tools\build.py'
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
