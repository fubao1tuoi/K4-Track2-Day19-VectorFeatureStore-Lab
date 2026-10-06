[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Windows PowerShell 5.1 otherwise inherits a legacy code page (often cp1252),
# while the lab prints Vietnamese text and Unicode arrows/check marks.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot
$WorkspaceRoot = Split-Path -Parent $RepoRoot
$SharedVenv = Join-Path $WorkspaceRoot ".venv"

# Keep Jupyter's writable runtime/signature databases inside the workspace.
# This also avoids permission issues on managed Windows machines.
$env:JUPYTER_DATA_DIR = Join-Path $RepoRoot ".jupyter-data"
$env:JUPYTER_RUNTIME_DIR = Join-Path $RepoRoot ".jupyter-runtime"
$env:IPYTHONDIR = Join-Path $RepoRoot ".ipython"

Write-Host "[lite/windows] Day 19 environment setup"

$version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) {
    throw "Python was not found. Install Python 3.10-3.14 and add it to PATH."
}
Write-Host "[lite/windows] System Python $version"

if (-not (Test-Path -LiteralPath (Join-Path $SharedVenv "Scripts\python.exe"))) {
    throw "Shared environment not found at $SharedVenv. Create it once from the workspace root with: python -m venv `"$SharedVenv`""
}

$VenvPython = Join-Path $SharedVenv "Scripts\python.exe"
Write-Host "[lite/windows] Using shared environment: $SharedVenv"

if (-not $SkipInstall) {
    Write-Host "[lite/windows] Installing dependencies"
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip" }
    & $VenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Could not install requirements.txt" }

    $needsDillOverride = & $VenvPython -c "import sys; print(int(sys.version_info >= (3, 14)))"
    if ($needsDillOverride -eq "1") {
        & $VenvPython -m pip install --upgrade "dill>=0.4,<1.0"
        if ($LASTEXITCODE -ne 0) { throw "Could not install the Python 3.14 dill override" }
    }
}

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

Write-Host "[lite/windows] Generating notebooks"
$notebookSources = @(Get-ChildItem -LiteralPath "notebooks" -Filter "*.py" |
    Where-Object { $_.BaseName -match '^\d{2}_' }
)
if ($notebookSources.Count -ne 8) {
    throw "Expected 8 numbered notebook sources, found $($notebookSources.Count)"
}
foreach ($source in $notebookSources) {
    & $VenvPython -m jupytext --to notebook --update $source.FullName
    if ($LASTEXITCODE -ne 0) { throw "Jupytext conversion failed for $($source.Name)" }
}

Write-Host "[lite/windows] Generating core and advanced datasets"
& $VenvPython scripts\seed_corpus.py
if ($LASTEXITCODE -ne 0) { throw "Core data generation failed" }
& $VenvPython scripts\gen_agent_queries.py
if ($LASTEXITCODE -ne 0) { throw "Agent-query generation failed" }
& $VenvPython scripts\gen_spend.py
if ($LASTEXITCODE -ne 0) { throw "Spend-data generation failed" }

Write-Host "[lite/windows] Running initial smoke checks"
& $VenvPython scripts\verify_lite.py
if ($LASTEXITCODE -ne 0) { throw "Initial verification failed" }

Write-Host ""
Write-Host "[lite/windows] Ready. Useful commands:"
Write-Host "  & `"$SharedVenv\Scripts\Activate.ps1`""
Write-Host "  python -m pytest -q"
Write-Host "  python scripts\benchmark.py"
Write-Host "  python -m uvicorn app.main:app --reload --port 8000"
Write-Host "  python -m jupyter lab --notebook-dir=notebooks"
