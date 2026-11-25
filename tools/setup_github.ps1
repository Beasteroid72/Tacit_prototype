# setup_github.ps1 -- Connect this project to your GitHub account.
# Git identity is already set: Beasteroid72 / daksh.shar74111@gmail.com
#
# Usage:
#   powershell -File setup_github.ps1                                          # just auth
#   powershell -File setup_github.ps1 https://github.com/Beasteroid72/<repo>    # + remote & push

param([string]$RepoUrl)

Write-Host "== 1) gh CLI =="
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "gh found: $((Get-Command gh).Source)"
} else {
    Write-Host "gh not installed -> install it from https://cli.github.com and re-run this script"
    exit 1
}

Write-Host "== 2) Auth status + login (interactive) =="
gh auth status 2>&1
gh auth login

Write-Host "== 3) Project remote =="
if (-not (Test-Path .git)) { git init -b main }
if ($RepoUrl) {
    git remote remove origin 2>$null | Out-Null
    git remote add origin $RepoUrl
    git add -A
    git commit -m "Add the app files" | Out-Null
    git push -u origin main
    Write-Host "Pushed to $RepoUrl"
} else {
    Write-Host "To link + push: powershell -File setup_github.ps1 https://github.com/Beasteroid72/<your-repo>"
}
