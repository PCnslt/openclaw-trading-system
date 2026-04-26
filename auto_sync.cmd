@echo off
rem Auto git sync for OpenClaw vault - runs every 4 hours
rem Uses Git Credential Manager (no hardcoded tokens)
cd /d "C:\Users\pcnsl\OneDrive\Documents\openclaw"
set GIT_TERMINAL_PROMPT=0

git remote set-url origin https://github.com/PCnslt/openclaw-trading-system.git 2>nul
git add -A 2>nul
git commit -m "auto-sync %DATE% %TIME%" 2>nul
git push origin master 2>nul
