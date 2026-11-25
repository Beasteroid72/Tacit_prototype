# build.ps1 -- builds the desktop app as a single windowed .exe.
#
#   powershell -File tools\build.ps1
#
# The result lands in dist\ as tacit_demo.exe, replacing the committed copy.
# Requires pyinstaller; the script installs it if it is missing.

$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}

pyinstaller -F -w `
    --name tacit_demo `
    --distpath dist `
    --workpath build `
    --specpath build `
    --paths desktop `
    desktop\run.py
