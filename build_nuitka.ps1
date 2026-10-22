$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python virtual environment not found: $python"
}

& $python -m nuitka `
    --mode=onefile `
    --lto=yes `
    --python-flag=no_docstrings `
    --include-package=mssql_python_odbc `
    --include-package-data=mssql_python_odbc `
    --user-package-configuration-file=mssql_python_odbc.nuitka-package.config.yml `
    --output-dir=build_nuitka `
    --output-filename=ImportExcel.exe `
    launcher.py

if ($LASTEXITCODE -ne 0) {
    throw "Nuitka build failed with exit code $LASTEXITCODE"
}

Write-Host 'Standalone completed.'
Write-Host 'Executable: build_nuitka\ImportExcel.exe'