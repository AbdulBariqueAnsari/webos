#!/usr/bin/env bash
set -e
echo "=================================================="
echo "     Web OS — Git Auto Commit & Push Tool"
echo "=================================================="
echo ""

if ! command -v git &> /dev/null; then
    echo "[ERROR] Git command not found!"
    exit 1
fi

echo "[1/3] Adding files..."
git add .

read -p "Enter commit message (Press ENTER for default): " msg
msg=${msg:-"Update Web OS: Fix screen freeze and add continuous live network IP monitor"}

echo "[2/3] Committing changes..."
git commit -m "$msg"

echo "[3/3] Pushing to GitHub..."
git push origin main

echo ""
echo "=================================================="
echo "   [SUCCESS] Successfully pushed to GitHub!"
echo "=================================================="
