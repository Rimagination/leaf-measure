param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonExe = "",
    [switch]$SkipInstall,
    [switch]$SkipAssets,
    [switch]$SkipFiji
)

$ErrorActionPreference = "Stop"

function Invoke-Python {
    param(
        [string[]]$CommandArgs
    )

    if ($script:PythonCommand) {
        & $script:PythonCommand @CommandArgs
    } else {
        & python @CommandArgs
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($CommandArgs -join ' ')"
    }
}

if ($PythonExe) {
    $script:PythonCommand = $PythonExe
} else {
    $script:PythonCommand = ""
}

$configDir = Join-Path $RepoRoot "config"
$runtimeExample = Join-Path $configDir "runtime.example.toml"
$runtimeConfig = Join-Path $configDir "runtime.toml"

if (-not (Test-Path $runtimeConfig) -and (Test-Path $runtimeExample)) {
    Copy-Item -LiteralPath $runtimeExample -Destination $runtimeConfig
    Write-Host "Created runtime config template at $runtimeConfig"
} else {
    Write-Host "Runtime config already exists or example template is missing."
}

if (-not $SkipInstall) {
    Write-Host "Installing leaf-measure into the current Python environment..."
    Push-Location $RepoRoot
    try {
        Invoke-Python -CommandArgs @("-m", "pip", "install", "-e", ".")
    } finally {
        Pop-Location
    }
}

$assetsRoot = Join-Path $RepoRoot ".leaf-measure-assets"
$assetsReady = (
    (Test-Path (Join-Path $assetsRoot "macros\original\Fameles_v2_Full_image.ijm")) -and
    (Test-Path (Join-Path $assetsRoot "macros\original\Fameles_v2_Thumbnails.ijm"))
)
if ($assetsReady) {
    Write-Host "Detected staged upstream assets: $assetsRoot"
} elseif ($SkipAssets) {
    Write-Host "Skipping upstream asset download. You can fetch them later with:"
    Write-Host '  python -m engine.cli fetch-assets'
} else {
    Write-Host "No staged upstream assets detected. Downloading from Figshare..."
    Push-Location $RepoRoot
    try {
        Invoke-Python -CommandArgs @("-m", "engine.cli", "fetch-assets", "--destination", $assetsRoot)
    } finally {
        Pop-Location
    }
}

$fijiCandidates = @(
    (Join-Path $RepoRoot "fiji-latest-win64-jdk\Fiji"),
    (Join-Path $RepoRoot "Fiji"),
    (Join-Path (Split-Path $RepoRoot -Parent) "leaf\fiji-latest-win64-jdk\Fiji")
)
$foundFiji = $fijiCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($foundFiji) {
    Write-Host "Detected Fiji candidate: $foundFiji"
} elseif ($SkipFiji) {
    Write-Host "Skipping Fiji download. You can fetch it later with:"
    Write-Host '  python -m engine.cli fetch-fiji'
} else {
    Write-Host "No local Fiji installation detected. Downloading the latest Fiji package..."
    Push-Location $RepoRoot
    try {
        Invoke-Python -CommandArgs @(
            "-m",
            "engine.cli",
            "fetch-fiji",
            "--destination",
            (Join-Path $RepoRoot "fiji-latest-win64-jdk")
        )
    } finally {
        Pop-Location
    }
    $foundFiji = Join-Path $RepoRoot "fiji-latest-win64-jdk\Fiji"
}

Write-Host "Next step:"
Write-Host '  python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode full'
Write-Host "Detected asset root: $assetsRoot"
if ($foundFiji) {
    Write-Host "Detected Fiji root: $foundFiji"
}

$doctorReport = Join-Path $configDir "doctor.json"
$doctorArgs = @("-m", "engine.cli", "doctor", "--output", $doctorReport)
if ($foundFiji) {
    $doctorArgs += @("--fiji", $foundFiji)
}
if (Test-Path $assetsRoot) {
    $doctorArgs += @("--assets", $assetsRoot)
}
Push-Location $RepoRoot
try {
    Invoke-Python -CommandArgs $doctorArgs
} finally {
    Pop-Location
}
Write-Host "Doctor report written to: $doctorReport"
