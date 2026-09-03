$ErrorActionPreference = "Stop"

$root = $PSScriptRoot

$exePath = Join-Path $root "ImportExcel.exe"

# Files to move after a successful import.
$sourceFiles = @(
    "data\File_Name.xls"
)

$processedDir = Join-Path $root "processed"
$logsDir = Join-Path $root "logs"

New-Item -ItemType Directory -Force -Path $processedDir | Out-Null
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

$logPath = Join-Path $logsDir "import_$timestamp.log"

Add-Content $logPath "[$(Get-Date)] Import started." -Encoding UTF8

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    Add-Content $logPath "[$(Get-Date)] ERROR: ImportExcel.exe was not found." -Encoding UTF8
    exit 1
}

foreach ($relativePath in $sourceFiles) {
    $sourcePath = Join-Path $root $relativePath
	
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        Add-Content $logPath "[$(Get-Date)] ERROR: Source file was not found: $sourcePath" -Encoding UTF8
        exit 1
    }
}

$output = & $exePath 2>&1
$exitCode = $LASTEXITCODE

$output | Add-Content -Path $logPath -Encoding UTF8

if ($exitCode -ne 0) {
    Add-Content $logPath "[$(Get-Date)] Import failed with exit code $exitCode." -Encoding UTF8
    exit $exitCode
}

Add-Content $logPath "[$(Get-Date)] Import completed successfully." -Encoding UTF8

foreach ($relativePath in $sourceFiles) {
    $sourcePath = Join-Path $root $relativePath

    $fileName = [System.IO.Path]::GetFileNameWithoutExtension($sourcePath)
    $extension = [System.IO.Path]::GetExtension($sourcePath)

    $archiveName = "${fileName}_$timestamp$extension"
    $archivePath = Join-Path $processedDir $archiveName

    Move-Item -LiteralPath $sourcePath -Destination $archivePath

    Add-Content $logPath "[$(Get-Date)] Moved '$sourcePath' to '$archivePath'." -Encoding UTF8
}

Add-Content $logPath "[$(Get-Date)] Script completed." -Encoding UTF8
exit 0