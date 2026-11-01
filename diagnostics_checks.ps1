$ErrorActionPreference = 'SilentlyContinue'
Write-Host '=== System Info ==='
hostname
Get-Date
Write-Host "PS Version: $($PSVersionTable.PSVersion)"
Write-Host ""

Write-Host '=== Top CPU Processes ==='
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Id, ProcessName, @{Name='CPU';Expression={[math]::Round($_.CPU,2)}}, @{Name='PM(MB)';Expression={[math]::Round($_.PM/1MB,2)}} | Format-Table -AutoSize
Write-Host ""

Write-Host '=== Listening Ports (11434,5000) ==='
Try { Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 11434,5000 | Format-Table -AutoSize } Catch { Write-Host '(nettcpconnection failed)' }
Write-Host ""

Write-Host '=== Test Ollama Port 11434 ==='
Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 | Format-List
Write-Host ""

$logs = Join-Path $env:APPDATA 'Code\logs'
Write-Host "=== VS Code logs path: $logs ==="
if (Test-Path $logs) {
    Get-ChildItem $logs -Recurse -File | Where-Object { $_.Name -match 'exthost|extensionhost|pylance|languageServer|output' -or $_.Extension -eq '.log' } | Sort-Object LastWriteTime -Descending | Select-Object -First 6 | ForEach-Object {
        Write-Host "--- FILE: $($_.FullName) (LastWrite: $($_.LastWriteTime)) ---"
        try { Get-Content $_.FullName -Tail 200 } catch { Write-Host '(failed to read file)' }
        Write-Host ''
    }
} else {
    Write-Host 'VS Code logs directory not found'
}

Write-Host '=== End Diagnostics ==='