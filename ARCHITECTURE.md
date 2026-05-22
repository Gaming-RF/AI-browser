# Architecture Documentation

## Overview

The AI Browser is designed with a modular, plugin-based architecture that allows it to work with any AI provider while maintaining a clean separation of concerns.

```
┌─────────────────────────────────────────────────────────────┐
│                      AIBrowser (Core)                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  AI Agent    │  │ Browser      │  │ Memory Manager   │ │
│  │  (Provider   │  │ Controller   │  │ (SQLite)         │ │
│  │   Agnostic)  │  │              │  │                  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │                    │                    │
    ┌────▼────┐          ┌────▼────┐         ┌────▼────┐
    │ OpenAI  │          │Playwright│         │ SQLite  │
    │ Claude  │          │ Browser  │         │ Database│
    │ Custom  │          │          │         │         │
    └─────────┘          └──────────┘         └─────────┘
```

## Components

### 1. Core Module (`src/core.py`)

The `AIBrowser` class is the main orchestrator that:
- Coordinates between AI agent, browser, and memory
- Parses AI responses and executes browser actions
- Logs interactions and maintains task state
- Provides a simple async interface for task execution

**Key Methods:**
- `execute_task()`: Main entry point for executing tasks
- `_build_prompt()`: Constructs prompts with context
- `_execute_ai_actions()`: Parses and executes AI decisions
- `_get_current_context()`: Gathers browser and memory state

### 2. AI Agents (`src/agents/`)

#### BaseAIAgent (Abstract)
Defines the interface all AI providers must implement:
- `send_message()`: Send a message to AI
- `vision_analyze()`: Analyze images
- `add_to_history()`: Maintain conversation history

#### Implementations
- **OpenAIAgent**: Uses OpenAI's GPT models
- **AnthropicAgent**: Uses Anthropic's Claude models
- Extensible to add more providers

#### Factory Pattern
The `create_agent()` factory function allows easy instantiation:
```python
agent = create_agent("openai", model="gpt-4")
agent = create_agent("anthropic", model="claude-3-opus-20240229")
```

### 3. Browser Controller (`src/browser/controller.py`)

The `BrowserController` class manages browser interactions using Playwright:
- Navigation
- Element clicking and interaction
- Form filling
- Screenshots
- JavaScript execution
- Waits and synchronization

**Features:**
- Action history tracking
- Async/await support
- Clean error handling

### 4. Memory Manager (`src/memory/manager.py`)

The `MemoryManager` class provides persistent storage:

**Tables:**
- `tasks`: Tracks executed tasks and their status
- `interactions`: Logs browser actions and AI decisions
- `context`: Stores key-value pairs for agent use

**Key Features:**
- Task logging and status tracking
- Interaction history
- Context persistence
- Query interface for retrieving information

## Data Flow

### Typical Execution Flow

```
1. User provides task description
   │
   ├─> AIBrowser.execute_task()
   │
   ├─> Log task in memory
   │
   ├─> Get current context (URL, history, saved state)
   │
   ├─> Build prompt with context
   │
   ├─> Send to AI agent
   │
   ├─> AI returns action (JSON format)
   │   Example: {"action": "click", "params": {"selector": ".search"}}
   │
   ├─> Parse action
   │
   ├─> Execute action via BrowserController
   │
   ├─> Log interaction in memory
   │
   ├─> If task not complete, loop back to step 5
   │
   └─> Return result and update task status
```

## AI Integration Pattern

The system is designed to work with any AI by:

1. **Standardized Interface**: BaseAIAgent defines what all providers must implement
2. **Prompt Engineering**: The prompt includes available actions and expected format
3. **Response Parsing**: Flexible JSON parsing of AI responses
4. **Action Mapping**: Each action name maps to a browser method

## Extension Points

### Adding a New AI Provider

```python
# Create src/agents/custom_agent.py
from src.agents.base_agent import BaseAIAgent

class CustomAgent(BaseAIAgent):
    async def send_message(self, message: str) -> str:
        # Your implementation
        pass
    
    async def vision_analyze(self, image_data: bytes, prompt: str) -> str:
        # Your implementation
        pass

# Update src/agents/factory.py
def create_agent(...):
    if provider_lower == "custom":
        from src.agents.custom_agent import CustomAgent
        return CustomAgent(...)
```

### Adding New Browser Actions

```python
# Add to BrowserController
async def new_action(self, param):
    result = await self.page.new_operation(param)
    action = BrowserAction(action_type="new_action", ...)
    self.action_history.append(action)
    return result

# Update _execute_action in AIBrowser
elif action == "new_action":
    result = await self.browser.new_action(params.get("param"))
```

### Custom Memory Backends

Replace SQLite with your own by extending `MemoryManager`:
```python
class CustomMemory(MemoryManager):
    def __init__(self, ...):
        # Your initialization
        pass
    
    def log_task(self, ...):
        # Your implementation
        pass
```

## Performance Considerations

1. **Memory**: Task and interaction history grows over time; consider cleanup policies
2. **Browser**: Reuse same page for multiple tasks to avoid startup overhead
3. **AI Calls**: Rate limiting may apply; consider batching interactions
4. **Context**: Keep context size reasonable for better AI performance

## Security Notes

1. **API Keys**: Never commit `.env` file; use environment variables
2. **Memory Storage**: SQLite file may contain sensitive data; protect accordingly
3. **Browser Automation**: Be cautious with automated login credentials
4. **Action Logging**: Interactions are logged; be aware of what data is stored

## Concurrency

The system is built on async/await for:
- Non-blocking browser operations
- Efficient AI API calls
- Better resource utilization

However, only one task should run at a time per `AIBrowser` instance to maintain state consistency.

## Testing Strategy

- Unit tests for individual components
- Integration tests for component interactions
- Mock AI responses for deterministic testing
- Snapshot tests for browser interactions
