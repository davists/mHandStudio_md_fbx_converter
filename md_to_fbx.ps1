# Process all .md files in the mao folder
Get-ChildItem -Path "mao\*.md" -Recurse | ForEach-Object {
    Write-Host "Processing: $($_.Name)" -ForegroundColor Cyan
    python mhand_to_fbx.py --input $_.FullName
}

Write-Host "Done!" -ForegroundColor Green
