# Alert Dashboard - PowerShell HTTP Server
# Uses Outlook COM to parse PST files. No API key required.
param([int]$Port = 8765)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Resolve

function Send-Response {
    param($ctx, [int]$status = 200, [string]$body = '', [string]$mime = 'application/json')
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $ctx.Response.StatusCode = $status
    $ctx.Response.ContentType = $mime
    $ctx.Response.ContentLength64 = $bytes.Length
    $ctx.Response.Headers.Add('Access-Control-Allow-Origin', '*')
    $ctx.Response.Headers.Add('Access-Control-Allow-Headers', 'Content-Type, X-Filename')
    $ctx.Response.Headers.Add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $ctx.Response.OutputStream.Close()
}

function Read-Body($req) {
    $ms = [System.IO.MemoryStream]::new()
    $req.InputStream.CopyTo($ms)
    return $ms.ToArray()
}

function Extract-EmailsFromPST($pstPath) {
    Write-Host "  Connecting to Outlook..."
    # Connect to Outlook: prefer the running instance (avoids CO_E_SERVER_EXEC_FAILURE)
    $outlook = $null
    try {
        $outlook = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application')
        Write-Host "  Attached to running Outlook instance."
    } catch {
        Write-Host "  Starting Outlook COM server..."
        try {
            $outlook = New-Object -ComObject Outlook.Application -ErrorAction Stop
        } catch {
            if ($_.Exception.Message -match '80080005|CO_E_SERVER_EXEC') {
                # Outlook is running but COM activation failed — wait and retry via GetActiveObject
                Write-Host "  COM activation conflict — retrying GetActiveObject in 2s..."
                Start-Sleep -Seconds 2
                try {
                    $outlook = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application')
                    Write-Host "  Retry succeeded."
                } catch {
                    throw "Outlook is open but COM automation is blocked. Try: close any Outlook dialog boxes, then retry the import."
                }
            } else {
                throw $_
            }
        }
    }
    $ns = $outlook.GetNamespace('MAPI')

    # Add the PST store if not already added
    $store = $ns.Stores | Where-Object { $_.FilePath -ieq $pstPath } | Select-Object -First 1
    if (-not $store) {
        $ns.AddStore($pstPath) | Out-Null
        Start-Sleep -Milliseconds 800
        $store = $ns.Stores | Where-Object { $_.FilePath -ieq $pstPath } | Select-Object -First 1
    }
    if (-not $store) { throw "Could not open PST store: $pstPath" }

    Write-Host "  Store: $($store.DisplayName)"
    $emails = [System.Collections.Generic.List[object]]::new()
    $idx = 0

    function Walk-Folder($folder, $folderPath) {
        $fp = if ($folderPath) { "$folderPath/$($folder.Name)" } else { $folder.Name }
        try {
            $items = $folder.Items
            $count = $items.Count
            for ($i = 1; $i -le $count; $i++) {
                try {
                    $item = $items.Item($i)
                    if ($item.Class -eq 43) {  # olMail = 43
                        $script:idx++
                        $subj = try { $item.Subject } catch { '' }
                        $sndr = try { $item.SenderName } catch { '' }
                        $sndrEmail = try { $item.SenderEmailAddress } catch { '' }
                        $dt = try { $item.ReceivedTime.ToString('yyyy-MM-ddTHH:mm:ss') } catch { '' }
                        # Only read body if it exists and is small
                        $body = try {
                            $b = $item.Body
                            if ($b -and $b.Length -gt 0) {
                                if ($b.Length -gt 2000) { $b.Substring(0, 2000) } else { $b }
                            } else { '' }
                        } catch { '' }

                        $emails.Add([PSCustomObject]@{
                            id           = $script:idx
                            subject      = $subj
                            sender       = $sndr
                            senderEmail  = $sndrEmail
                            date         = $dt
                            body         = $body
                            folder       = $fp
                        }) | Out-Null
                    }
                } catch { }
            }
        } catch { }
        try {
            foreach ($sub in $folder.Folders) { Walk-Folder $sub $fp }
        } catch { }
    }

    $root = $store.GetRootFolder()
    Walk-Folder $root ''
    Write-Host "  Extracted $($emails.Count) emails."
    return $emails
}

# ── Start listener ────────────────────────────────────────────────────────────
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
try {
    $listener.Start()
} catch {
    Write-Host ""
    Write-Host "  ERROR: Could not start server on port $Port" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Is another instance already running? Check Task Manager for powershell.exe" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "  Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "  Alert Intelligence Dashboard"
Write-Host "  ============================`n"
Write-Host "  Open: http://127.0.0.1:$Port"
Write-Host "  Press Ctrl+C to stop.`n"

try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        $method = $req.HttpMethod
        $path = $req.Url.LocalPath

        # CORS preflight
        if ($method -eq 'OPTIONS') {
            Send-Response $ctx 204 ''
            continue
        }

        # Serve index.html
        if ($method -eq 'GET' -and ($path -eq '/' -or $path -eq '/index.html')) {
            $file = Join-Path $scriptDir 'index.html'
            $bytes = [System.IO.File]::ReadAllBytes($file)
            $ctx.Response.StatusCode = 200
            $ctx.Response.ContentType = 'text/html; charset=utf-8'
            $ctx.Response.ContentLength64 = $bytes.Length
            $ctx.Response.Headers.Add('Access-Control-Allow-Origin', '*')
            $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
            $ctx.Response.OutputStream.Close()
            continue
        }

        # Process PST — accept raw binary body (application/octet-stream)
        if ($method -eq 'POST' -and $path -eq '/api/analyse') {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Processing PST upload..."
            $tempPath = $null
            try {
                # Save uploaded bytes to temp PST file
                $bodyBytes = Read-Body $req
                Write-Host "  Received $($bodyBytes.Length) bytes"
                $tempPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName() + '.pst')
                [System.IO.File]::WriteAllBytes($tempPath, $bodyBytes)
                Write-Host "  Saved to: $tempPath"

                $emails = Extract-EmailsFromPST $tempPath
                $json = $emails | ConvertTo-Json -Depth 4 -Compress
                Send-Response $ctx 200 $json
                Write-Host "  Done. Returned $($emails.Count) emails.`n"
            } catch {
                $msg = $_.Exception.Message -replace '"', "'"
                Send-Response $ctx 500 "{`"error`":`"$msg`"}"
                Write-Host "  ERROR: $_`n"
            } finally {
                if ($tempPath -and (Test-Path $tempPath)) {
                    try { Remove-Item $tempPath -Force } catch { }
                }
            }
            continue
        }

        # 404
        Send-Response $ctx 404 '{"error":"Not found"}'
    }
} catch {
    Write-Host ""
    Write-Host "  FATAL ERROR: $_" -ForegroundColor Red
    Read-Host "  Press Enter to exit"
} finally {
    $listener.Stop()
    Write-Host "Server stopped."
}
