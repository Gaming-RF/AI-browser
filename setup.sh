#!/bin/sh
set -e

echo "=== Starting AI-browser Setup for Linux ==="

# Check for python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but not installed." >&2
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment (.venv)..."
    python3 -m venv .venv || {
        echo "Error: Failed to create virtual environment. Please install python3-venv (e.g., sudo apt install python3-venv)." >&2
        exit 1
    }
fi

# Activate virtual environment
echo "Activating virtual environment..."
. .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# Install Playwright browser binaries
echo "Installing Playwright browsers..."
playwright install

# Setup frontend dependencies
if [ -d "electron-app" ]; then
    echo "Setting up electron-app node modules..."
    cd electron-app
    if ! command -v npm >/dev/null 2>&1; then
        echo "Warning: npm is not installed. Skipping Electron app dependency installation." >&2
    else
        npm install --no-audit --no-fund
    fi
    cd ..
fi

echo "=== Setup completed successfully! ==="
