# TMRDS FieldLab for Windows 11 x64 — locally installed Python wheel bundle
# Offline after the previously built, hash-inventoried ZIP has been copied to this laptop.
# No admin privilege, public API, login, local web server, or background updates required.
param(
  [string] $BundleDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string] $InstallDir = "",
  [switch] $SkipSmoke
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if ([Environment]::Is64BitOperatingSystem -ne $true -or $env:OS -ne "Windows_NT") {
  throw "This FieldLab wheel pack targets Windows x64."
}
$BundleDir = [System.IO.Path]::GetFullPath($BundleDir)
if ([string]::IsNullOrWhiteSpace($InstallDir)) { $InstallDir = Join-Path $BundleDir ".fieldlab-venv" }
$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$Wheels = Join-Path $BundleDir "wheelhouse"
$Manifest = Join-Path $BundleDir "wheelhouse-manifest.json"
$Requirements = Join-Path $BundleDir "deploy\fieldlab\requirements.txt"
$VerifyScript = Join-Path $BundleDir "scripts\fieldlab_wheelhouse.py"
$FieldLabCli = Join-Path $BundleDir "scripts\fieldlab_cli.py"
foreach ($item in @($Wheels, $Manifest, $Requirements, $VerifyScript, $FieldLabCli)) {
  if (-not (Test-Path -LiteralPath $item)) {
    throw "FieldLab bundle is incomplete. No installation was attempted."
  }
}
if (Test-Path -LiteralPath $InstallDir) {
  throw "Installation directory already exists. Move it manually before installing again; no silent overwrite."
}
& py -3.11 -c "import platform,sys; assert platform.architecture()[0]=='64bit' and sys.version_info[:2]==(3,11)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 x64 (with Python Launcher) must be installed before disconnecting." }
& py -3.11 $VerifyScript verify $Wheels --manifest $Manifest --platform win_amd64 --python-abi cp311
if ($LASTEXITCODE -ne 0) { throw "Offline wheelhouse checksum verification failed. No packages installed." }
$env:PIP_NO_INDEX = "1"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PIP_NO_PYTHON_VERSION_WARNING = "1"
& py -3.11 -m venv $InstallDir
if ($LASTEXITCODE -ne 0) { throw "Could not create isolated local Python environment." }
$Python = Join-Path $InstallDir "Scripts\python.exe"
& $Python -m pip install --no-index --only-binary=:all: --find-links $Wheels -r $Requirements
if ($LASTEXITCODE -ne 0) {
  throw "Offline dependency installation failed. Review the local wheel list; do not enable automatic downloads."
}
& $Python -m pip check
if ($LASTEXITCODE -ne 0) { throw "Installed dependencies do not satisfy their declared requirements." }
if (-not $SkipSmoke) {
  & $Python $FieldLabCli status
  if ($LASTEXITCODE -ne 0) { throw "FieldLab library import smoke failed." }
  & $Python $FieldLabCli molecule --smiles CCO
  if ($LASTEXITCODE -ne 0) { throw "FieldLab RDKit execution smoke failed." }
}
Write-Host "Offline FieldLab libraries installed. No patient files were read and no external service was contacted."
Write-Host "CLI: & '$Python' '$FieldLabCli' status"
Write-Host "Desktop: & '$Python' '$BundleDir\scripts\fieldlab_desktop.py'"
Write-Host "Research-only metadata/math: NOT a diagnostic, prescribing or treatment device."
