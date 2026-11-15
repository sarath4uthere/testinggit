<#
Windows helper so you do not need bash for local work.
Examples:
  .\run.ps1 test                 # run unit tests in Docker
  .\run.ps1 up                   # build and start the dev stack  (http://localhost:8090)
  .\run.ps1 up -Target test      # another environment           (http://localhost:8091)
  .\run.ps1 logs                 # follow logs
  .\run.ps1 status               # containers
  .\run.ps1 monitoring           # add Prometheus + Grafana
  .\run.ps1 down                 # stop, keep data
  .\run.ps1 reset                # stop AND delete the database volume
#>
param(
  [Parameter(Position = 0)][string]$Command = "help",
  [string]$Target = "dev",
  [string]$Tag = "local"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$envFile = "env/$Target.env"
if (-not (Test-Path $envFile)) { throw "Unknown environment '$Target' (no $envFile)" }
$project = "shop-$Target"
$env:TAG = $Tag

function Compose { docker compose -p $project --env-file $envFile -f docker-compose.yml @args }
function WebPort { (Select-String -Path $envFile -Pattern '^WEB_PORT=(\d+)').Matches[0].Groups[1].Value }

switch ($Command) {
  "test"       { docker build --target test -t shop-api-test:latest ./api }
  "up"         { Compose up -d --build --wait --wait-timeout 180; Write-Host "Open http://localhost:$(WebPort)" }
  "down"       { Compose down }
  "reset"      { Compose down -v }
  "logs"       { Compose logs -f }
  "status"     { Compose ps }
  "monitoring" {
    docker compose -p $project --env-file $envFile -f docker-compose.yml -f docker-compose.monitoring.yml up -d
    Write-Host "Prometheus http://localhost:9090   Grafana http://localhost:3000 (admin / admin-change-me)"
  }
  default      { Get-Content $PSCommandPath -TotalCount 12 }
}
