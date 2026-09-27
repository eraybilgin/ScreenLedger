param(
    [string]$Version = '0.1.0'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot

$python = Join-Path $projectRoot '.build-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    py -3.11 -m venv '.build-venv'
}
& $python -m pip install -r 'requirements.txt' -r 'packaging\requirements-build.txt'
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies could not be installed.' }

& $python -m PyInstaller --noconfirm --clean --windowed --onedir `
    --name ScreenLedger --distpath dist --workpath build --specpath build `
    --paths app --hidden-import arayuz --hidden-import excel_rapor app\takip.py
if ($LASTEXITCODE -ne 0) { throw 'The application bundle could not be built.' }

$bundledExe = Join-Path $projectRoot 'dist\ScreenLedger\ScreenLedger.exe'
$check = Start-Process -FilePath $bundledExe -ArgumentList '--self-test' `
    -WindowStyle Hidden -Wait -PassThru
if ($check.ExitCode -ne 0) { throw 'The application bundle failed its import check.' }

$compilerCandidates = @(
    (Join-Path $projectRoot '.build-tools\InnoSetup\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 7\ISCC.exe',
    'C:\Program Files\Inno Setup 7\ISCC.exe'
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) {
    throw 'Inno Setup 7 (ISCC.exe) is required to build the installer.'
}
& $compiler ('/DAppVersion=' + $Version) 'packaging\ScreenLedger.iss'
if ($LASTEXITCODE -ne 0) { throw 'The installer could not be compiled.' }

$setup = Join-Path $projectRoot ('release\ScreenLedger-Setup-' + $Version + '.exe')
Get-Item -LiteralPath $setup | Select-Object FullName, Length
Get-FileHash -LiteralPath $setup -Algorithm SHA256
