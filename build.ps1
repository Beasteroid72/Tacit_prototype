# build.ps1 -- builds the Tacit app as a onefile windowed executable (creates dist\<exe>).
# Requires pyinstaller (pip install pyinstaller); the script installs it if missing.
Set-Location $PSScriptRoot
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) { pip install pyinstaller }
$entry = Get-ChildItem -Filter *demo*.py
pyinstaller -F -w $entry.FullName
