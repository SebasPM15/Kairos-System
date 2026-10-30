# Starts the backend against the demo database and vault (never the real ones).
# Usage (from the repo root): .\scripts\demo.ps1 [-Reset] [-Port 8000] [-Database demo.db]
param(
    [switch]$Reset,
    [int]$Port = 8000,
    [string]$Database = "demo.db"
)

$backend = Join-Path $PSScriptRoot "..\backend"
$vault = Join-Path $env:TEMP "kairos-demo-vault"
New-Item -ItemType Directory -Force $vault | Out-Null

Push-Location $backend
try {
    & .\.venv\Scripts\Activate.ps1
    $env:DATABASE_URL = "sqlite:///./$Database"
    $env:OBSIDIAN_VAULT_PATH = $vault
    $env:MAX_ACTIVE_PROJECTS = "3"

    alembic upgrade head
    if ($Reset) { python scripts/seed_demo.py --reset } else { python scripts/seed_demo.py }
    # Without -Reset, an already-seeded database is refused on purpose and kept as is

    uvicorn app.main:app --reload --port $Port
}
finally {
    Pop-Location
}
