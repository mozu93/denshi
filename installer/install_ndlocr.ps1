# install_ndlocr.ps1
# ndlocr-lite OCR engine installer script
# Called from Inno Setup [Run] section (runs under PowerShell 5.1)

$ErrorActionPreference = "Stop"

function Find-Uv {
    $candidates = @(
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:LOCALAPPDATA\uv\bin\uv.exe"
    )
    $fromPath = Get-Command uv -ErrorAction SilentlyContinue
    if ($fromPath) { $candidates = @($fromPath.Source) + $candidates }
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return $null
}

function Find-NdlOcr {
    $candidates = @(
        "$env:USERPROFILE\.local\bin\ndlocr-lite.exe"
    )
    $fromPath = Get-Command ndlocr-lite -ErrorAction SilentlyContinue
    if ($fromPath) { $candidates = @($fromPath.Source) + $candidates }
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return $null
}

# --- Already installed? ---
$existing = Find-NdlOcr
if ($existing) {
    Write-Host "ndlocr-lite is already installed: $existing"
    exit 0
}

# --- Find or install uv ---
$uvExe = Find-Uv
if (-not $uvExe) {
    Write-Host "uv not found. Installing uv..."
    try {
        $installScript = (Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing).Content
        Invoke-Expression $installScript
        $env:PATH = "$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\uv\bin;" + $env:PATH
        $uvExe = Find-Uv
    } catch {
        Write-Host "ERROR: Failed to install uv: $_"
        exit 1
    }
}

if (-not $uvExe) {
    Write-Host "ERROR: uv not found after installation."
    Write-Host "  Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

Write-Host "Using uv: $uvExe"

# --- Install ndlocr-lite ---
Write-Host "Installing ndlocr-lite (this may take several minutes)..."
try {
    & $uvExe tool install "git+https://github.com/ndl-lab/ndlocr-lite"
    if ($LASTEXITCODE -ne 0) { throw "exit code: $LASTEXITCODE" }
} catch {
    Write-Host "ERROR: Failed to install ndlocr-lite: $_"
    exit 1
}

# --- Verify ---
$env:PATH = "$env:USERPROFILE\.local\bin;" + $env:PATH
$installed = Find-NdlOcr
if ($installed) {
    Write-Host "ndlocr-lite installed successfully: $installed"
    exit 0
} else {
    Write-Host "WARNING: Installation completed but executable not found."
    Write-Host "  It will be recognized after restarting."
    exit 0
}
