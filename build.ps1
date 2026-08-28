$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not $env:VIRTUAL_ENV) {
    throw "Virtual environment is not active."
}

python -m PyInstaller `
    --clean `
    --noconfirm `
	ImportExcel.spec

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Host "Build completed successfully: dist\ImportExcel.exe"