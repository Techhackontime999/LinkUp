#!/bin/bash
# Show all git commits including reverted ones

echo "=== ALL COMMITS (INCLUDING REVERTED) ==="
echo ""

# Show reflog with commit messages
git reflog --format="%C(yellow)%h%C(reset) - %C(green)(%ar)%C(reset) %C(white)%s%C(reset) %C(dim)- %an%C(reset)"

echo ""
echo "=== DETAILED VIEW OF RECENT COMMITS ==="
echo ""

# Show last 20 commits from reflog with full details
git log --walk-reflogs --oneline --decorate -20
