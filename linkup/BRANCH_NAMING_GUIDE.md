# 🌿 Professional Branch Naming Guide

## Branch Naming Convention

Use the format: `<type>/<description>`

### Branch Types

| Type | Purpose | Example |
|------|---------|---------|
| `feature/` | New features | `feature/user-authentication` |
| `fix/` | Bug fixes | `fix/login-validation-error` |
| `hotfix/` | Critical production fixes | `hotfix/security-vulnerability` |
| `refactor/` | Code refactoring | `refactor/database-queries` |
| `docs/` | Documentation updates | `docs/api-documentation` |
| `test/` | Adding/updating tests | `test/user-registration` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |
| `experiment/` | Experimental features | `experiment/new-ui-design` |
| `release/` | Release preparation | `release/v1.2.0` |

### Naming Rules

1. **Use kebab-case**: `feature/user-profile-page`
2. **Be descriptive**: `fix/navbar-mobile-responsive`
3. **Keep it short**: Max 50 characters
4. **No spaces**: Use hyphens instead
5. **Lowercase only**: `feature/oauth-integration`

### Examples

✅ **Good Branch Names**
```
feature/multimedia-upload
fix/search-results-pagination
hotfix/memory-leak-issue
refactor/user-service-layer
docs/deployment-instructions
test/integration-test-suite
chore/eslint-configuration
```

❌ **Bad Branch Names**
```
new_feature
fixing_bugs
UpdateUserProfile
feature/adding-new-feature-for-user-authentication-with-oauth
temp-branch
test123
```

### Current Professional Branches

- `feature/multimedia-upload` - Multimedia upload functionality
- `hotfix/revert-multimedia-changes` - Revert multimedia changes
- `chore/branch-setup-files` - Branch setup configuration files