# 🔄 Professional Git Workflow

## Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(auth): add OAuth login` |
| `fix` | Bug fix | `fix(ui): resolve mobile navbar` |
| `docs` | Documentation | `docs(readme): update setup guide` |
| `style` | Code formatting | `style(css): fix indentation` |
| `refactor` | Code refactoring | `refactor(api): optimize queries` |
| `perf` | Performance improvement | `perf(db): add query indexes` |
| `test` | Adding tests | `test(auth): add login unit tests` |
| `chore` | Maintenance | `chore(deps): update packages` |

### Workflow Steps

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make Changes & Commit**
   ```bash
   git add .
   git commit -m "feat(scope): add new functionality"
   ```

3. **Push to GitHub**
   ```bash
   git push origin feature/new-feature
   ```

4. **Create Pull Request**
   - Use GitHub UI to create PR
   - Add descriptive title and description
   - Request code review

5. **Merge to Main**
   - Use "Squash and merge" for clean history
   - Delete feature branch after merge

### Best Practices

- ✅ Write clear, descriptive commit messages
- ✅ Keep commits small and focused
- ✅ Use conventional commit format
- ✅ Test before committing
- ✅ Use meaningful branch names
- ❌ Don't commit directly to main
- ❌ Don't use vague messages like "fix bug"
- ❌ Don't commit large, unrelated changes together

### Git Hooks

This repository includes:
- **commit-msg hook**: Validates commit message format
- **Commit template**: Provides format guidance

### Example Workflow

```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b feature/user-dashboard

# Make changes
# ... code changes ...

# Commit with proper format
git add .
git commit -m "feat(dashboard): add user statistics widget"

# Push and create PR
git push origin feature/user-dashboard
# Create PR on GitHub

# After review and approval
# Merge via GitHub UI
# Delete branch
git checkout main
git pull origin main
git branch -d feature/user-dashboard
```