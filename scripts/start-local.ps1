$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Instale Python 3.12 ou superior e adicione ao PATH." }
python -c "import sys; assert sys.version_info >= (3,12), 'Use Python 3.12 ou superior'"
if ($LASTEXITCODE -ne 0) { throw "Versão do Python incompatível." }
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar a venv." }
}
$PythonExe = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $PythonExe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências." }
$env:DJANGO_DEBUG = "1"
& $PythonExe manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Falha nas migrações." }
& $PythonExe manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw "Falha ao preparar os arquivos estáticos." }
Write-Host "API em http://127.0.0.1:8000/api/docs/ — Ctrl+C para parar."
& $PythonExe manage.py runserver 127.0.0.1:8000
