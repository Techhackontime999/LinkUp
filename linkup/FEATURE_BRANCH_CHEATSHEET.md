# Feature Branch Cheat Sheet

## 🚀 Quick Start

```bash
# 1. Create feature branch
git checkout main
git pull origin main
git checkout -b feature/my-new-feature

# 2. Work on feature
# ... edit files ...
git add .
git commit -m "Add new feature"

# 3. Push to GitHub
git push -u origin feature/my-new-feature

# 4. Create Pull Request on GitHub
# Go to GitHub → Click "Compare & pull request"

# 5. After merge, clean up
git checkout main
git pull origin main
git branch -d feature/my-new-feature
```

## 📋 Common Commands

| Task | Command |
|------|---------|
| Create branch | `git checkout -b feature/name` |
| Switch branch | `git checkout feature/name` |
| List branches | `git branch -a` |
| Push branch | `git push -u origin feature/name` |
| Delete local | `git branch -d feature/name` |
| Delete remote | `git push origin --delete feature/name` |
| Update from main | `git merge origin/main` |

## 🏷️ Branch Naming

```bash
feature/user-auth          # New feature
bugfix/login-error         # Bug fix
hotfix/security-patch      # Urgent fix
improve/performance        # Improvement
```

## ✅ Best Practices

1. ✅ Always start from updated `main`
2. ✅ One feature = one branch
3. ✅ Commit often with clear messages
4. ✅ Test before merging
5. ✅ Clean up after merge

## ❌ Don't Do This

1. ❌ Work directly on `main`
2. ❌ Use vague branch names
3. ❌ Mix multiple features
4. ❌ Let branches live for weeks
5. ❌ Forget to pull before creating branch

---

**Remember:** Feature branches keep your code organized and professional! 🎯
