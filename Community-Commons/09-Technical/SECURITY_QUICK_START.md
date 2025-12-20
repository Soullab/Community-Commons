# 🚀 Security Immune System - Quick Start Guide

**Get protected in 10 minutes or less**

---

## Installation (5 minutes)

### 1. Install Git Pre-Commit Hook
```bash
# Create the hook
cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/bash
echo "🔒 Running security checks..."

PATTERNS=(
    'sk-ant-api03-[A-Za-z0-9_-]{95,}'
    'sk-[A-Za-z0-9]{48}'
    'xox[baprs]-[0-9a-zA-Z-]{10,}'
    'ghp_[0-9a-zA-Z]{36}'
    'AKIA[0-9A-Z]{16}'
    'password\s*=\s*["\047][^"\047]{8,}'
    'api[_-]?key\s*=\s*["\047][^"\047]{8,}'
)

FILES=$(git diff --cached --name-only --diff-filter=ACM)

for file in $FILES; do
    if [ -f "$file" ]; then
        for pattern in "${PATTERNS[@]}"; do
            if grep -qE "$pattern" "$file" 2>/dev/null; then
                echo "❌ COMMIT BLOCKED! Found secret in: $file"
                echo "Move secrets to .env file instead"
                exit 1
            fi
        done
    fi
done

echo "✅ No secrets detected"
exit 0
HOOK

# Make it executable
chmod +x .git/hooks/pre-commit

echo "✅ Git hook installed!"
```

### 2. Update .gitignore
```bash
# Add these patterns
cat >> .gitignore << 'IGNORE'
.env
.env.local
.env.*.local
*.key
*.pem
secrets.*
credentials.*
IGNORE

echo "✅ .gitignore updated!"
```

### 3. Create Security Scripts Directory
```bash
mkdir -p ~/scripts

# Download or create security-audit.sh
# (See full implementation in SECURITY_IMMUNE_SYSTEM.md)

chmod +x ~/scripts/security-audit.sh
echo "✅ Security scripts ready!"
```

---

## Usage (2 minutes)

### Test Your Protection
```bash
# This should be BLOCKED:
echo "API_KEY=sk-ant-fake123" > test.txt
git add test.txt
git commit -m "test"

# Cleanup
rm test.txt
git reset HEAD
```

### Run Security Audit
```bash
bash ~/scripts/security-audit.sh
```

### Monitor .env Integrity
```bash
# First time: create checksum
shasum -a 256 ~/.env > ~/.env.checksum

# Anytime: verify integrity
bash ~/scripts/env-monitor.sh
```

---

## Daily Use

### Before Every Commit
The git hook runs automatically. If blocked:
1. Remove the secret from the file
2. Add it to `.env` instead
3. Verify `.env` is in `.gitignore`
4. Commit again

### Weekly (5 minutes)
```bash
# Run full security audit
bash ~/scripts/security-audit.sh

# Review and fix any issues
```

### After .env Changes
```bash
# Update the checksum
shasum -a 256 ~/.env > ~/.env.checksum
```

---

## Emergency: API Key Exposed

```bash
# 1. Rotate key at provider (Anthropic Console, etc.)
# 2. Update .env
echo "ANTHROPIC_API_KEY=new_key_here" > ~/.env

# 3. Clean old key from history
OLD_KEY="old_key_value"
grep -v "$OLD_KEY" ~/.zsh_history > ~/.zsh_history.tmp
mv ~/.zsh_history.tmp ~/.zsh_history

# 4. Update checksum
shasum -a 256 ~/.env > ~/.env.checksum

# 5. Verify
bash ~/scripts/security-audit.sh
```

---

## Automation (Optional)

### Set Up Automated Checks
```bash
bash ~/scripts/setup-security-schedule.sh
```

Choose:
- **Option 3** (recommended): Daily .env checks + Weekly audits
- **Option 4**: Manual only (you run scripts yourself)

---

## Common Issues

### "Permission denied" on git hook
```bash
chmod +x .git/hooks/pre-commit
```

### .env still tracked by git
```bash
git rm --cached .env
git commit -m "Remove .env from tracking"
```

### False positive in security scan
Edit the script to exclude specific patterns or files.

---

## Quick Reference

| Task | Command |
|------|---------|
| Test git hook | Try committing a secret |
| Run audit | `bash ~/scripts/security-audit.sh` |
| Check .env | `bash ~/scripts/env-monitor.sh` |
| Update checksum | `shasum -a 256 ~/.env > ~/.env.checksum` |
| View hooks | `ls -la .git/hooks/pre-commit` |

---

## Next Steps

1. ✅ Install the system (above)
2. ✅ Test it works
3. ✅ Run first audit
4. 📖 Read full guide: `SECURITY_IMMUNE_SYSTEM.md`
5. 🤖 Set up automation (optional)
6. 📅 Schedule weekly audits
7. 🔄 Rotate API keys every 90 days

---

**Time to secure:** ~10 minutes
**Time to maintain:** ~5 minutes/week
**Peace of mind:** Priceless

---

*Part of the Soullab Community Commons*
*For the full guide, see: SECURITY_IMMUNE_SYSTEM.md*
