# Quick Reference

## Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
python -m playwright install

# Set environment variables
# Windows PowerShell:
$env:OPENAI_API_KEY="sk-..."
$env:AI_PROVIDER="openai"

# Linux/Mac:
export OPENAI_API_KEY="sk-..."
export AI_PROVIDER="openai"
```

## Basic Usage

### Interactive Mode
```bash
python main.py
```

### Python Script
```python
import asyncio
from src.core import AIBrowser

async def main():
    browser = AIBrowser(ai_provider="openai")
    await browser.initialize()
    
    try:
        result = await browser.execute_task("Your task here")
        print(result)
    finally:
        await browser.close()

asyncio.run(main())
```

## Available AI Providers

| Provider | Model | Setup |
|----------|-------|-------|
| OpenAI | gpt-4, gpt-3.5-turbo | `OPENAI_API_KEY` env var |
| Anthropic | claude-3-opus-20240229 | `ANTHROPIC_API_KEY` env var |
| Custom | your choice | Implement BaseAIAgent |

## Common Tasks

### Search and Collect Data
```python
await browser.execute_task("Go to Google, search for 'Python', and save top 5 results")
```

### Form Filling
```python
await browser.execute_task("Navigate to form and fill with name='John' and email='john@example.com'")
```

### Login
```python
browser.save_context("creds", {"user": "john", "pass": "secret"})
await browser.execute_task("Log in with saved credentials")
```

### Multi-step Workflow
```python
for task in ["Step 1", "Step 2", "Step 3"]:
    await browser.execute_task(task)
```

## Memory Operations

```python
# Save data
browser.save_context("key", {"data": "value"})

# Retrieve data
data = browser.get_context("key")

# Get all context
all_data = browser.memory.get_all_context()

# View task history
history = browser.get_task_history(limit=10)
```

## Browser Actions

Supported actions (called by AI):
- `navigate(url)` - Go to URL
- `click(selector)` - Click element
- `type_text(selector, text)` - Fill form field
- `screenshot()` - Capture page
- `get_content()` - Get page HTML
- `evaluate_js(code)` - Run JavaScript
- `press_key(key)` - Press keyboard key
- `wait_for_selector(selector)` - Wait for element
- `save_context(key, value)` - Store data

## Environment Variables

```
AI_PROVIDER=openai              # or "anthropic"
AI_MODEL=gpt-4                  # Model name
OPENAI_API_KEY=sk-...           # OpenAI key
ANTHROPIC_API_KEY=sk-ant-...    # Anthropic key
HEADLESS_MODE=true              # Show/hide browser
BROWSER_SLOW_MO=0               # Delay in ms
MEMORY_DB_PATH=memory.db        # Database path
TASK_TIMEOUT=300                # Timeout in seconds
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module not found | Activate venv: `venv\Scripts\activate` |
| API key error | Set env vars or edit .env file |
| Browser won't start | Run `python -m playwright install` |
| Timeout errors | Increase TASK_TIMEOUT or debug with headless=false |
| Memory persists | Delete `memory.db` file to reset |

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_ai_browser.py::test_browser_controller_initialization

# Verbose output
pytest -v tests/
```

## File Locations

- **Config**: `src/config.py`
- **Core Logic**: `src/core.py`
- **Agents**: `src/agents/*.py`
- **Browser**: `src/browser/controller.py`
- **Memory**: `src/memory/manager.py`
- **Database**: `memory.db` (auto-created)

## Resources

- README.md - Project overview
- SETUP.md - Detailed setup
- ARCHITECTURE.md - System design
- ADVANCED_USAGE.md - Advanced features
- examples.py - Code examples

## Support

For issues or questions:
1. Check the documentation files
2. Review examples.py
3. Check task history for errors
4. Run with headless=false to debug
5. Check error messages in console
