#!/bin/sh
set -e

echo "=== Starting AI-browser Update for Linux ==="

# Perform Git pull
if [ -d ".git" ]; then
    echo "Pulling latest updates from Git..."
    git pull --rebase
else
    echo "Warning: Not a git repository. Skipping Git update."
fi

# Run setup to refresh dependencies
echo "Running setup logic to update packages..."
if [ -f "./setup.sh" ]; then
    ./setup.sh
else
    # Fallback inline logic if setup.sh is missing
    if [ -d ".venv" ]; then
        echo "Activating virtual environment..."
        . .venv/bin/activate
        echo "Installing Python dependencies..."
        pip install -r requirements.txt
        playwright install
    fi

    if [ -d "electron-app" ] && command -v npm >/dev/null 2>&1; then
        echo "Updating electron-app node modules..."
        cd electron-app
        npm install --no-audit --no-fund
        cd ..
    fi
fi

echo "=== Update completed successfully! ==="
