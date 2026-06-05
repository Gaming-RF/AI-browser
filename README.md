# AI Browser Agent

An autonomous AI-powered browser that can take control of your browser, perform tasks, and remember what it does.

## Features

- **Browser Automation**: Control browser actions (navigation, clicking, filling forms, etc.)
- **Memory System**: Persist and retrieve information about previous interactions
- **Multi-AI Support**: Works with any AI provider (OpenAI, Anthropic, or custom)
- **Task Execution**: Autonomous task execution based on natural language instructions
- **Action History**: Complete audit trail of all browser interactions

## Architecture

```
src/
  ├── browser/       # Browser control & automation
  ├── memory/        # Memory & context management
  ├── agents/        # AI agent interfaces & implementations
  └── core.py        # Main orchestrator
config/
  └── config.yaml    # Configuration file
tests/              # Test files
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install
```

## Quick Start

```python
from src.core import AIBrowser

# Initialize browser
browser = AIBrowser(ai_provider="openai")

# Execute a task
result = await browser.execute_task("Find the price of Python books on Amazon")
```

## Configuration

Edit `config/config.yaml` to configure:
- AI Provider (OpenAI, Anthropic, etc.)
- Memory settings
- Browser headless mode
- Task execution parameters

## Supported AI Providers

- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude)
- Custom providers (implement the `BaseAIAgent` interface)
