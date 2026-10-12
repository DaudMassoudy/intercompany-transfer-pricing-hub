param(
  [int]$AppPreferred = 3000,
  [int]$ApiPreferred = 8000,
  [int]$N8nPreferred = 5678,
  [int]$MinioPreferred = 9001,
  [int]$SearchRange = 100
)

function Test-PortInUse([int]$Port) {
  try {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    if ($null -ne $listener) { return $true }
  } catch {
    # Fallback for Windows environments where Get-NetTCPConnection is restricted.
    $match = netstat -ano -p tcp 2>$null | Select-String -Pattern (":$Port\s+.*LISTENING")
    if ($match) { return $true }
  }
  return $false
}

function Find-FreePort([int]$Preferred, [int]$MaxOffset) {
  for ($p = $Preferred; $p -le ($Preferred + $MaxOffset); $p++) {
    if (-not (Test-PortInUse $p)) { return $p }
  }
  throw "No free TCP port found in range $Preferred-$($Preferred + $MaxOffset)."
}

try {
  $app   = Find-FreePort $AppPreferred $SearchRange
  $api   = Find-FreePort $ApiPreferred $SearchRange
  $n8n   = Find-FreePort $N8nPreferred $SearchRange
  $minio = Find-FreePort $MinioPreferred $SearchRange

  Write-Output "APP_HOST_PORT=$app"
  Write-Output "API_HOST_PORT=$api"
  Write-Output "N8N_HOST_PORT=$n8n"
  Write-Output "MINIO_CONSOLE_HOST_PORT=$minio"
  $appFallback = if ($app -ne $AppPreferred) { 'true' } else { 'false' }
  $apiFallback = if ($api -ne $ApiPreferred) { 'true' } else { 'false' }
  $n8nFallback = if ($n8n -ne $N8nPreferred) { 'true' } else { 'false' }
  $minioFallback = if ($minio -ne $MinioPreferred) { 'true' } else { 'false' }
  Write-Output "APP_PORT_FALLBACK=$appFallback"
  Write-Output "API_PORT_FALLBACK=$apiFallback"
  Write-Output "N8N_PORT_FALLBACK=$n8nFallback"
  Write-Output "MINIO_PORT_FALLBACK=$minioFallback"
  exit 0
} catch {
  Write-Error $_.Exception.Message
  exit 21
}
