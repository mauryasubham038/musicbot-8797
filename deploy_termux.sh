#!/data/data/com.termux/files/usr/bin/bash
# Termux me chalao:  bash deploy_termux.sh
# 1) GitHub repo banata + push karta hai  2) Render ka one-tap deploy link deta hai
set -e
pkg install -y git gh >/dev/null 2>&1 || true

if ! gh auth status >/dev/null 2>&1; then
  echo ">> GitHub login (browser/token): "
  gh auth login
fi

REPO="musicbot-$(date +%s | tail -c 5)"
[ -d .git ] || git init -q
git add .
git commit -qm "music bot" || true
git branch -M main
# public repo: Render ka one-tap link public repo par chalta hai. Secrets (.env) .gitignore se bahar hain.
gh repo create "$REPO" --public --source=. --remote=origin --push
URL=$(gh repo view --json url -q .url)

echo
echo "✅ Code GitHub par: $URL"
echo "👉 Ab ye link browser me kholo (Render login ke baad env vars bharo):"
echo "https://render.com/deploy?repo=$URL"
echo
echo "Env me daalna: API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, OWNER_IDS"
