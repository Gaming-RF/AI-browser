# Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- An API key from either OpenAI or Anthropic (or both)

## Installation Steps

### 1. Clone or Download the Project

```bash
cd path/to/Ai\ Browser
```

### 2. Create Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
python -m playwright install
```

### 5. Set Up Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
# For OpenAI:
#   OPENAI_API_KEY=sk-...

# For Anthropic:
#   ANTHROPIC_API_KEY=sk-ant-...
```

Or set environment variables directly:

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-..."
$env:AI_PROVIDER="openai"

# macOS/Linux
export OPENAI_API_KEY="sk-..."
export AI_PROVIDER="openai"
```

## Quick Start

### Option 1: Interactive Mode

```bash
python main.py
```

Follow the prompts to enter your task.

### Option 2: Using Examples

```python
# Edit examples.py to uncomment the example you want
python examples.py
```

### Option 3: Python Script

```python
import asyncio
from src.core import AIBrowser

async def main():
    browser = AIBrowser(ai_provider="openai")
    await browser.initialize()
    
    try:
        result = await browser.execute_task("Go to Google and search for 'Python'")
        print(result)
    finally:
        await browser.close()

asyncio.run(main())
```

## Configuration

Edit `.env` to customize:

- `AI_PROVIDER`: Choose between "openai" or "anthropic"
- `AI_MODEL`: Specify the model to use
- `HEADLESS_MODE`: Set to false to see the browser window
- `BROWSER_SLOW_MO`: Add delay between actions (in milliseconds)

## Testing

Run tests to verify installation:

```bash
pytest tests/
```

## Troubleshooting

### Issue: "OPENAI_API_KEY not found"
- Make sure your `.env` file is in the root directory
- Verify the API key is correctly formatted
- Try setting the environment variable directly

### Issue: "Playwright not installed"
```bash
python -m playwright install
```

### Issue: "Module not found" errors
```bash
# Make sure you're in the virtual environment
pip install -r requirements.txt
```

## File Structure

```
Ai Browser/
├── src/
│   ├── agents/          # AI agent implementations
│   ├── browser/         # Browser control module
│   ├── memory/          # Memory management
│   ├── core.py         # Main orchestrator
│   └── config.py       # Configuration
├── tests/              # Test files
├── examples.py         # Usage examples
├── main.py            # Entry point
├── requirements.txt   # Dependencies
├── .env.example       # Environment template
├── .gitignore        # Git ignore rules
└── README.md         # Project documentation
```

## Next Steps

1. Read the README.md for feature overview
2. Check examples.py for different use cases
3. Explore the source code to understand the architecture
4. Extend with custom AI providers or browser actions
