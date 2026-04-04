param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    python -m engine.cli sync-skills --repo-root $RepoRoot
} finally {
    Pop-Location
}
