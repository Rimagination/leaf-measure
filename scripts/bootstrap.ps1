param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$configDir = Join-Path $RepoRoot "config"
$runtimeExample = Join-Path $configDir "runtime.example.toml"
$runtimeConfig = Join-Path $configDir "runtime.toml"

if (-not (Test-Path $runtimeConfig) -and (Test-Path $runtimeExample)) {
    Copy-Item -LiteralPath $runtimeExample -Destination $runtimeConfig
    Write-Host "Created runtime config template at $runtimeConfig"
} else {
    Write-Host "Runtime config already exists or example template is missing."
}

$candidates = @(
    (Join-Path $RepoRoot "fiji-latest-win64-jdk\\Fiji"),
    (Join-Path $RepoRoot "Fiji"),
    (Join-Path (Split-Path $RepoRoot -Parent) "leaf\\fiji-latest-win64-jdk\\Fiji")
)

$found = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($found) {
    Write-Host "Detected Fiji candidate: $found"
} else {
    Write-Host "No local Fiji installation detected. Configure FIJI_DIR or edit config/runtime.toml."
    Write-Host "If you are using an agent, ask it to search for 'fiji-windows-x64.exe' and then either:"
    Write-Host "  1. pass --fiji <Fiji-dir> to the CLI"
    Write-Host "  2. write that path into config/runtime.toml"
}

Write-Host "Next step:"
Write-Host '  python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode full'
Write-Host "If upstream assets are not bundled, stage them first with:"
Write-Host '  .\scripts\stage-assets.ps1 -SourceRoot "<downloaded-or-extracted-upstream-package>"'
