param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [string]$DestinationRoot = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $DestinationRoot) {
    $DestinationRoot = Join-Path $repoRoot ".leaf-measure-assets"
}

$sourceRoot = (Resolve-Path $SourceRoot).Path

$macroCandidates = @(@(
    (Join-Path $sourceRoot "data\\Fameles_v2_Full_image.ijm"),
    (Join-Path $sourceRoot "Fameles_v2_Full_image.ijm")
) | Where-Object { Test-Path $_ })

$thumbCandidates = @(@(
    (Join-Path $sourceRoot "data\\Fameles_v2_Thumbnails.ijm"),
    (Join-Path $sourceRoot "Fameles_v2_Thumbnails.ijm")
) | Where-Object { Test-Path $_ })

$trialCandidates = @(@(
    (Join-Path $sourceRoot "data\\Trial\\Trial\\01_input"),
    (Join-Path $sourceRoot "Trial\\Trial\\01_input")
) | Where-Object { Test-Path $_ })

$goldenCandidates = @(@(
    (Join-Path $sourceRoot "golden"),
    (Join-Path $sourceRoot "data\\golden")
) | Where-Object { Test-Path $_ })

if (-not $macroCandidates -or -not $thumbCandidates) {
    throw "Could not find FAMeLeS macro files under $sourceRoot"
}

New-Item -ItemType Directory -Force -Path (Join-Path $DestinationRoot "macros\\original") | Out-Null
Copy-Item -LiteralPath $macroCandidates[0] -Destination (Join-Path $DestinationRoot "macros\\original\\Fameles_v2_Full_image.ijm") -Force
Copy-Item -LiteralPath $thumbCandidates[0] -Destination (Join-Path $DestinationRoot "macros\\original\\Fameles_v2_Thumbnails.ijm") -Force

if ($trialCandidates) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DestinationRoot "fixtures\\trial_input") | Out-Null
    Get-ChildItem -LiteralPath $trialCandidates[0] | Where-Object { -not $_.Name.StartsWith(".") } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $DestinationRoot "fixtures\\trial_input") -Recurse -Force
    }
}

if ($goldenCandidates) {
    Copy-Item -LiteralPath $goldenCandidates[0] -Destination (Join-Path $DestinationRoot "golden") -Recurse -Force
}

Write-Host "Staged assets into $DestinationRoot"
Write-Host "Next step:"
Write-Host "  set LEAF_MEASURE_ASSETS_DIR=$DestinationRoot"
Write-Host '  python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode full --assets "<assets-dir>"'
