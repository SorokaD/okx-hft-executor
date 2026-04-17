param(
    [Parameter(Mandatory = $false)]
    [string] $DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    Write-Host "DATABASE_URL is empty. Set env DATABASE_URL or pass -DatabaseUrl 'postgresql://...'" -ForegroundColor Red
    exit 2
}

$psql = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psql) {
    Write-Host "psql not found in PATH. Install PostgreSQL client tools or add psql.exe to PATH." -ForegroundColor Red
    exit 2
}

$sqlPath = Join-Path $PSScriptRoot "positions_updated_at_trigger.sql"
if (-not (Test-Path -LiteralPath $sqlPath)) {
    Write-Host "SQL file not found: $sqlPath" -ForegroundColor Red
    exit 2
}

Write-Host "Applying: $sqlPath"
& $psql.Source $DatabaseUrl -v ON_ERROR_STOP=1 -f $sqlPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "OK"
