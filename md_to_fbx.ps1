param(
    [string]$RootPath = "mao",
    [switch]$UseLegacy = $false
)

# Use OCR version by default (more reliable)
$scriptName = if ($UseLegacy) { "mhand_to_fbx.py" } else { "mhand_to_fbx_ocr.py" }

Write-Host "================================================" -ForegroundColor Yellow
Write-Host "  mHand MD to FBX Batch Converter" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "Root Path: $RootPath" -ForegroundColor Cyan
Write-Host "Script: $scriptName" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $RootPath)) {
    Write-Host "ERROR: Path '$RootPath' not found!" -ForegroundColor Red
    exit 1
}

$mdFiles = Get-ChildItem -Path "$RootPath\*.md" -Recurse

if ($mdFiles.Count -eq 0) {
    Write-Host "No .md files found in '$RootPath'" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($mdFiles.Count) .md file(s)" -ForegroundColor Green
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($file in $mdFiles) {
    Write-Host "Processing: $($file.Name)" -ForegroundColor Cyan
    Write-Host "  Path: $($file.FullName)" -ForegroundColor Gray
    
    python $scriptName --input $file.FullName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Success" -ForegroundColor Green
        $successCount++
    } else {
        Write-Host "  Failed" -ForegroundColor Red
        $failCount++
    }
    Write-Host ""
}

Write-Host "================================================" -ForegroundColor Yellow
Write-Host "  Batch Conversion Complete" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "Total: $($mdFiles.Count) | Success: $successCount | Failed: $failCount" -ForegroundColor Cyan
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "All conversions completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Some conversions failed. Check logs above." -ForegroundColor Yellow
}
