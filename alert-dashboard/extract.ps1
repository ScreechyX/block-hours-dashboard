# Alert Dashboard - PST Extractor
# Run this script directly (double-click or right-click > Run with PowerShell)
# It will ask you to pick a PST file, extract all emails, and open the dashboard.

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Resolve
$outFile = Join-Path $scriptDir 'alerts.json'

Write-Host ""
Write-Host "  Alert Intelligence - PST Extractor"
Write-Host "  ==================================`n"

# ── Pick PST file via GUI dialog ──────────────────────────────
Add-Type -AssemblyName System.Windows.Forms | Out-Null
$dialog = [System.Windows.Forms.OpenFileDialog]::new()
$dialog.Title  = "Select PST File to Analyse"
$dialog.Filter = "Outlook PST Files (*.pst)|*.pst|All Files (*.*)|*.*"
$dialog.InitialDirectory = [Environment]::GetFolderPath('UserProfile')

Write-Host "  Opening file picker..."
if ($dialog.ShowDialog() -ne 'OK') {
    Write-Host "  Cancelled." -ForegroundColor Yellow
    Read-Host "`n  Press Enter to exit"
    exit 0
}
$pstPath = $dialog.FileName
Write-Host "  Selected: $pstPath`n"

# ── Connect to Outlook ────────────────────────────────────────
Write-Host "  Connecting to Outlook..."
$outlook = $null

# Try the running instance first (avoids CO_E_SERVER_EXEC_FAILURE)
try {
    $outlook = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application')
    Write-Host "  Attached to running Outlook.`n"
} catch {
    Write-Host "  Starting Outlook..."
    try {
        $outlook = New-Object -ComObject Outlook.Application -ErrorAction Stop
        Write-Host "  Outlook started.`n"
    } catch {
        Write-Host ""
        Write-Host "  ERROR: Could not connect to Outlook." -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Make sure Microsoft Outlook is installed." -ForegroundColor Yellow
        Read-Host "`n  Press Enter to exit"
        exit 1
    }
}

$ns = $outlook.GetNamespace('MAPI')

# ── Add PST store ─────────────────────────────────────────────
Write-Host "  Opening PST store..."
$store = $ns.Stores | Where-Object { $_.FilePath -ieq $pstPath } | Select-Object -First 1
if (-not $store) {
    $ns.AddStore($pstPath) | Out-Null
    Start-Sleep -Milliseconds 1000
    $store = $ns.Stores | Where-Object { $_.FilePath -ieq $pstPath } | Select-Object -First 1
}
if (-not $store) {
    Write-Host "  ERROR: Could not open PST store." -ForegroundColor Red
    Read-Host "`n  Press Enter to exit"
    exit 1
}
Write-Host "  Store: $($store.DisplayName)`n"

# ── Walk folders and extract emails ───────────────────────────
$emails = [System.Collections.Generic.List[object]]::new()
$idx    = 0

function Walk-Folder($folder, $folderPath) {
    $fp = if ($folderPath) { "$folderPath/$($folder.Name)" } else { $folder.Name }
    try {
        $items = $folder.Items
        $count = $items.Count
        if ($count -gt 0) { Write-Host "    [$count] $fp" }
        for ($i = 1; $i -le $count; $i++) {
            try {
                $item = $items.Item($i)
                if ($item.Class -eq 43) {
                    $script:idx++
                    $subj  = try { $item.Subject } catch { '' }
                    $sndr  = try { $item.SenderName } catch { '' }
                    $dt    = try { $item.ReceivedTime.ToString('yyyy-MM-ddTHH:mm:ss') } catch { '' }
                    $body  = try {
                        $b = $item.Body
                        if ($b -and $b.Length -gt 0) { $b.Substring(0, [Math]::Min($b.Length, 2000)) } else { '' }
                    } catch { '' }

                    $emails.Add([PSCustomObject]@{
                        id      = $script:idx
                        subject = $subj
                        sender  = $sndr
                        date    = $dt
                        body    = $body
                        folder  = $fp
                    }) | Out-Null
                }
            } catch { }
        }
    } catch { }
    try {
        foreach ($sub in $folder.Folders) { Walk-Folder $sub $fp }
    } catch { }
}

Write-Host "  Scanning folders..."
Walk-Folder $store.GetRootFolder() ''
Write-Host ""
Write-Host "  Extracted $($emails.Count) emails." -ForegroundColor Green

# ── Save JSON ─────────────────────────────────────────────────
Write-Host "  Saving to: $outFile"
$emails | ConvertTo-Json -Depth 4 -Compress | Set-Content $outFile -Encoding UTF8
Write-Host "  Done!" -ForegroundColor Green

# ── Open dashboard ────────────────────────────────────────────
$dashPath = Join-Path $scriptDir 'dashboard.html'
Write-Host ""
Write-Host "  Opening dashboard in browser..."
Start-Process $dashPath
Write-Host ""
Write-Host "  When the dashboard opens, click 'Load Alerts' and select alerts.json"
Write-Host "  (It's saved next to this script: $outFile)"
Write-Host ""
Read-Host "  Press Enter to exit"
