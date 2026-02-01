# 🚀 Quick Start: Upload to GitHub

## Step 1: Install Git

### Windows
Download and install Git from: https://git-scm.com/download/win

Or use winget:
```powershell
winget install Git.Git
```

After installation, restart your terminal/PowerShell.

### Verify Installation
```bash
git --version
```

## Step 2: Configure Git (First Time Only)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 3: Check for Sensitive Files

Before uploading, verify these files are NOT in your project:
- ❌ `.env` (should be ignored)
- ❌ `db.sqlite3` (should be ignored)
- ❌ Files in `logs/` with sensitive data
- ❌ Files in `media/` with private content

Your `.gitignore` is already configured to exclude these!

## Step 4: Initialize Git Repository

Open PowerShell/Terminal in your project folder:

```bash
# Navigate to project
cd C:\Users\ADMIN\Downloads\linkup\linkup

# Initialize git
git init

# Add all files
git add .

# Check what will be committed
git status

# Make first commit
git commit -m "Initial commit: Production-ready LinkUp application"
```

## Step 5: Create GitHub Repository

1. Go to: https://github.com/new
2. Repository name: `linkup`
3. Description: "Professional networking platform - Django LinkedIn clone"
4. Choose **Public** or **Private**
5. **DO NOT** check any boxes (no README, .gitignore, or license)
6. Click **"Create repository"**

## Step 6: Connect and Push

GitHub will show you commands. Use these:

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/linkup.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

### If you get authentication error:

You'll need a Personal Access Token:

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "LinkUp Upload"
4. Select scopes: `repo` (full control)
5. Click "Generate token"
6. **COPY THE TOKEN** (you won't see it again!)

When pushing, use:
- Username: your GitHub username
- Password: paste the token (not your GitHub password)

## Step 7: Verify Upload

1. Go to: `https://github.com/YOUR_USERNAME/linkup`
2. Check files are there
3. Verify README.md displays correctly
4. Confirm no sensitive files (.env, db.sqlite3) are uploaded

## ✅ Done!

Your project is now on GitHub! 🎉

## What's Excluded (by .gitignore)

These files/folders are automatically excluded:
- `__pycache__/` - Python cache
- `*.pyc`, `*.pyo` - Compiled Python
- `db.sqlite3` - Database file
- `.env` - Environment variables
- `media/` - User uploads
- `staticfiles/` - Collected static files
- `logs/` - Log files
- `venv/`, `env/` - Virtual environments
- `.vscode/`, `.idea/` - IDE files

## Next Steps

After uploading to GitHub:

1. ✅ **Add repository description and topics** on GitHub
2. 🔄 **Deploy to production** (see DEPLOYMENT.md)
3. 🔄 **Setup CI/CD** (optional)
4. 🔄 **Invite collaborators** (if team project)

## Common Issues

### "Permission denied (publickey)"
Use HTTPS instead of SSH, or setup SSH key:
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/linkup.git
```

### "Large files detected"
GitHub has 100MB file limit. Check:
```bash
# Find large files
Get-ChildItem -Recurse | Where-Object {$_.Length -gt 50MB} | Select-Object FullName, Length
```

### "Authentication failed"
Use Personal Access Token instead of password (see Step 6).

## Need Help?

- Read: `GITHUB_UPLOAD_GUIDE.md` for detailed instructions
- Visit: https://docs.github.com/en/get-started
- Check: https://git-scm.com/doc

---

**Ready to deploy?** See `DEPLOYMENT.md` for production deployment guides!
