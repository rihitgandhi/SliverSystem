$base = "http://127.0.0.1:5000"
$results = @()
function Test-Get($path) {
  try {
    $r = Invoke-WebRequest -Uri ($using:base + $path) -Method GET -TimeoutSec 30 -UseBasicParsing
    $body = $r.Content
    if ($body.Length -gt 200) { $body = $body.Substring(0,200) }
    return [pscustomobject]@{Endpoint="GET $path"; Status=$r.StatusCode; Notes=($body -replace "\s+"," ").Substring(0,[Math]::Min(120,$body.Length))}
  } catch {
    $sc = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
    return [pscustomobject]@{Endpoint="GET $path"; Status=$sc; Notes=$_.Exception.Message}
  }
}
function Test-Post($path,$body) {
  try {
    $json = $body | ConvertTo-Json -Depth 6 -Compress
    $r = Invoke-WebRequest -Uri ("http://127.0.0.1:5000" + $path) -Method POST -Body $json -ContentType 'application/json' -TimeoutSec 120 -UseBasicParsing
    $c = $r.Content
    if ($c.Length -gt 200) { $c = $c.Substring(0,200) }
    return [pscustomobject]@{Endpoint="POST $path"; Status=$r.StatusCode; Notes=($c -replace "\s+"," ")}
  } catch {
    $sc = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
    $detail = ""
    try { $s = $_.Exception.Response.GetResponseStream(); $sr = New-Object IO.StreamReader($s); $detail = $sr.ReadToEnd(); if ($detail.Length -gt 160) {$detail=$detail.Substring(0,160)} } catch {}
    return [pscustomobject]@{Endpoint="POST $path"; Status=$sc; Notes=("$($_.Exception.Message) | $detail")}
  }
}

$gets = '/','/index.html','/chat.html','/score.html','/help.html','/Blog_1.html','/api/health','/css/main.css','/scripts/tool-shared.js','/scripts/chatbot.js'
foreach ($g in $gets) {
  try {
    $r = Invoke-WebRequest -Uri ("http://127.0.0.1:5000" + $g) -Method GET -TimeoutSec 30 -UseBasicParsing
    $body = $r.Content
    if ($body.Length -gt 120) { $body = $body.Substring(0,120) }
    $results += [pscustomobject]@{Endpoint="GET $g"; Status=$r.StatusCode; Notes=($body -replace "\s+"," ")}
  } catch {
    $sc = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
    $results += [pscustomobject]@{Endpoint="GET $g"; Status=$sc; Notes=$_.Exception.Message}
  }
}

$results += Test-Post '/api/chat' @{message="What is WCAG?"; conversation_id="test"}
$results += Test-Post '/api/score' @{url="https://example.com"}
# 1x1 transparent PNG base64
$png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
$results += Test-Post '/api/alt-text' @{image=$png; detail_level="medium"; context=""; tone="neutral"}
$results += Test-Post '/api/review-code' @{code="<button>click</button>"; code_type="html"}
$results += Test-Post '/api/simplify-content' @{content="The quick brown fox jumps over the lazy dog."; reading_level="grade5"; simplification_level="medium"; content_type="general"}

$results | Format-Table -AutoSize -Wrap
