#!/bin/bash
# Setup script for Claire_claude. Run once after cloning or on a new machine.
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Setting up Claire_claude"

# 1. Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment..."
  python3 -m venv .venv
fi

# 2. Install dependencies
echo "==> Installing dependencies..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

# 3. Check for .env
if [ ! -f ".env" ]; then
  echo "==> WARNING: .env not found. Copy .env.example to .env and fill in your credentials."
  echo "    cp .env.example .env"
fi

# 4. Check for Google auth credentials
if [ ! -f "auth/credentials.json" ]; then
  echo "==> WARNING: auth/credentials.json not found. Add your Google OAuth credentials to proceed with Google-dependent tools."
fi

echo ""
echo "==> Setup complete. Activate the environment with:"
echo "    source .venv/bin/activate"
