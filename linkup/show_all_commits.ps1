# PowerShell script to show all git commits including reverted ones

Write-Host "=== ALL COMMITS (INCLUDING REVERTED) ===" -ForegroundColor Cyan
Write-Host ""

# Show reflog with commit messages
git log --walk-reflogs --pretty=format:"%C(yellow)%h%C(reset) %C(green)%ad%C(reset) - %C(white)%s%C(reset)" --date=relative -30

Write-Host ""
Write-Host ""
Write-Host "=== COMMIT HASH REFERENCE ===" -ForegroundColor Cyan
Write-Host ""

# Show all commits from reflog
git reflog --format="%h - %gs" -30
