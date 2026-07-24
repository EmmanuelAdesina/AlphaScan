#!/bin/bash
"""
AlphaScan GitHub Deployment Setup Script.
Configures git, sets up remote with token authentication, and handles missing tokens.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AlphaScan GitHub Setup Script v0.5   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Check if .git directory exists ──────────────────────────────
if [ -d ".git" ]; then
    echo -e "${GREEN}✓ Git repository exists${NC}"
else
    echo -e "${YELLOW}⚠ No .git directory found. Initializing new repository...${NC}"
    git init
    echo -e "${GREEN}✓ Git repository initialized${NC}"
fi

# ── Step 2: Set git config ──────────────────────────────────────────────
git config user.name "AlphaScan" 2>/dev/null || true
git config user.email "alphascan@bot.local" 2>/dev/null || true

# Check if user.name and user.email are set
if [ -z "$(git config user.name)" ]; then
    git config user.name "AlphaScan"
    echo -e "${GREEN}✓ Git user.name set to 'AlphaScan'${NC}"
else
    echo -e "${GREEN}✓ Git user.name: $(git config user.name)${NC}"
fi

if [ -z "$(git config user.email)" ]; then
    git config user.email "alphascan@bot.local"
    echo -e "${GREEN}✓ Git user.email set to 'alphascan@bot.local'${NC}"
else
    echo -e "${GREEN}✓ Git user.email: $(git config user.email)${NC}"
fi

echo ""

# ── Step 3: Check for GitHub token ──────────────────────────────────────
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

if [ -f ".env" ]; then
    # Try to extract GITHUB_TOKEN from .env
    ENV_TOKEN=$(grep -o 'GITHUB_TOKEN=[^"'"'"']*' .env 2>/dev/null | head -1 | cut -d'=' -f2)
    if [ -n "$ENV_TOKEN" ]; then
        GITHUB_TOKEN="$ENV_TOKEN"
    fi
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}⚠ GitHub token is MISSING${NC}"
    echo -e "${YELLOW}  To deploy to GitHub, you need to:${NC}"
    echo -e "${YELLOW}  1. Create a token at: https://github.com/settings/tokens${NC}"
    echo -e "${YELLOW}  2. Add GITHUB_TOKEN=your_token to .env file${NC}"
    echo ""
    echo -e "${YELLOW}  Continuing without GitHub push capability.${NC}"
    echo ""
    exit 0
fi

echo -e "${GREEN}✓ GitHub token found${NC}"

# ── Step 4: Get remote URL from git config───────────────────────────────
REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")

if [ -z "$REMOTE_URL" ]; then
    echo -e "${YELLOW}⚠ No remote 'origin' configured.${NC}"
    echo -e "${YELLOW}  Please set up your remote manually:${NC}"
    echo -e "${YELLOW}  git remote add origin https://github.com/YOUR_USER/AlphaScan.git${NC}"
    echo ""
    exit 0
fi

echo -e "${GREEN}✓ Remote origin: $REMOTE_URL${NC}"

# ── Step 5: Set up remote with token authentication ─────────────────────
# Reconstruct URL with token
if echo "$REMOTE_URL" | grep -q "github.com"; then
    # Extract owner/repo from URL
    if echo "$REMOTE_URL" | grep -q "git@github.com:"; then
        # SSH format: git@github.com:owner/repo.git
        REPO_PATH=$(echo "$REMOTE_URL" | sed 's|git@github.com:||')
    elif echo "$REMOTE_URL" | grep -q "https://"; then
        # HTTPS format: https://github.com/owner/repo.git
        REPO_PATH=$(echo "$REMOTE_URL" | sed 's|https://github.com/||' | sed 's|^/||')
    else
        REPO_PATH=""
    fi

    if [ -n "$REPO_PATH" ]; then
        # Set remote with token authentication
        AUTH_URL="https://${GITHUB_TOKEN}@github.com/${REPO_PATH}"
        git remote set-url origin "$AUTH_URL"
        echo -e "${GREEN}✓ Remote configured with token authentication${NC}"
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   GitHub setup complete!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "To push to GitHub, run: ${BLUE}git push -u origin main${NC}"
echo ""