$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://localhost:3000/")
$listener.Start()
Write-Host "Serving on http://localhost:3000/"
$root = Split-Path $MyInvocation.MyCommand.Path | Split-Path
while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $req = $ctx.Request
    $res = $ctx.Response
    $path = $req.Url.LocalPath.TrimStart('/')
    if ($path -eq '' -or $path -eq '/') { $path = 'index.html' }

    if ($path -eq 'api/adonis-refresh') {
        $scriptPath = Join-Path $root 'adonis_refresh.py'
        try {
            $output = & python $scriptPath 2>&1 | Where-Object { $_ -match '^\s*[\[{]' } | Select-Object -First 1
            if (-not $output) { $output = '{"error":"Script produced no output"}' }
        } catch {
            $output = '{"error":"' + ($_.Exception.Message -replace '"','\"') + '"}'
        }
        $res.ContentType = 'application/json; charset=utf-8'
        $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$output)
        $res.ContentLength64 = $bytes.Length
        $res.OutputStream.Write($bytes, 0, $bytes.Length)
        $res.OutputStream.Close()
        continue
    }

    $file = Join-Path $root $path
    if (Test-Path $file -PathType Leaf) {
        $ext = [System.IO.Path]::GetExtension($file)
        $mime = switch ($ext) {
            '.html' { 'text/html; charset=utf-8' }
            '.js'   { 'application/javascript' }
            '.css'  { 'text/css' }
            '.json' { 'application/json' }
            '.png'  { 'image/png' }
            '.svg'  { 'image/svg+xml' }
            default { 'application/octet-stream' }
        }
        $bytes = [System.IO.File]::ReadAllBytes($file)
        $res.ContentType = $mime
        $res.ContentLength64 = $bytes.Length
        $res.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
        $res.StatusCode = 404
    }
    $res.OutputStream.Close()
}
