# Advanced Usage Guide

## Table of Contents
1. Context and Memory
2. Multi-Step Tasks
3. Custom AI Providers
4. Error Handling
5. Performance Optimization
6. Debugging

## 1. Context and Memory

### Saving and Retrieving Context

The AI Browser can remember information across tasks:

```python
import asyncio
from src.core import AIBrowser

async def example():
    browser = AIBrowser()
    await browser.initialize()
    
    try:
        # Save context
        browser.save_context("user_credentials", {
            "username": "myuser",
            "password": "***"
        })
        
        # Retrieve context
        creds = browser.get_context("user_credentials")
        print(creds)  # {"username": "myuser", "password": "***"}
        
    finally:
        await browser.close()
```

### Using Context in Tasks

The context is automatically included in the AI prompt:

```python
# The AI will know about saved context
await browser.execute_task(
    "Log in to my account using the saved credentials"
)
```

## 2. Multi-Step Tasks

### Sequential Task Execution

```python
async def complex_workflow():
    browser = AIBrowser()
    await browser.initialize()
    
    try:
        tasks = [
            "Navigate to Amazon",
            "Search for 'laptop'",
            "Filter by price: $500-$1000",
            "Sort by customer rating",
            "Save the top 3 products to context"
        ]
        
        for task in tasks:
            result = await browser.execute_task(task)
            print(f"✓ {task}")
            if result['status'] == 'failed':
                print(f"  Error: {result['error']}")
                break
        
        # Retrieve saved products
        products = browser.get_context("top_products")
        print("Top Products:", products)
        
    finally:
        await browser.close()

asyncio.run(complex_workflow())
```

### Task Dependencies

```python
async def workflow_with_dependencies():
    browser = AIBrowser()
    await browser.initialize()
    
    try:
        # Step 1: Login
        result1 = await browser.execute_task("Log in to my account")
        if result1['status'] != 'success':
            print("Login failed!")
            return
        
        # Step 2: Get user data (depends on login)
        result2 = await browser.execute_task("Navigate to profile and save user data")
        
        # Step 3: Use saved data
        user_data = browser.get_context("user_data")
        print(f"User: {user_data}")
        
    finally:
        await browser.close()
```

## 3. Custom AI Providers

### Creating a Custom Provider

```python
# src/agents/custom_provider_agent.py
from src.agents.base_agent import BaseAIAgent

class CustomProviderAgent(BaseAIAgent):
    """Custom AI provider implementation."""
    
    def __init__(self, model: str, api_key: str = None):
        super().__init__(model, api_key)
        # Initialize your custom provider
        
    async def send_message(self, message: str) -> str:
        # Implement your API call
        # Make sure to maintain conversation history
        self.add_to_history("user", message)
        
        # Call your custom AI service
        response = await self._call_custom_api(message)
        
        self.add_to_history("assistant", response)
        return response
    
    async def vision_analyze(self, image_data: bytes, prompt: str) -> str:
        # Implement image analysis
        response = await self._analyze_image(image_data, prompt)
        return response
    
    async def _call_custom_api(self, message: str) -> str:
        # Your custom implementation
        pass
    
    async def _analyze_image(self, image_data: bytes, prompt: str) -> str:
        # Your custom implementation
        pass
```

### Registering Custom Provider

```python
# Update src/agents/factory.py
def create_agent(provider: str, model: str = None, api_key: str = None):
    provider_lower = provider.lower()
    
    # ... existing code ...
    
    elif provider_lower == "custom":
        from src.agents.custom_provider_agent import CustomProviderAgent
        return CustomProviderAgent(model=model or "custom-model", api_key=api_key)
    
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

### Using Custom Provider

```python
browser = AIBrowser(ai_provider="custom", model="custom-model")
await browser.initialize()
```

## 4. Error Handling

### Basic Error Handling

```python
async def safe_task_execution():
    browser = AIBrowser()
    
    try:
        await browser.initialize()
        
        result = await browser.execute_task("Do something")
        
        if result['status'] == 'failed':
            print(f"Task failed: {result['error']}")
        else:
            print(f"Task succeeded: {result['result']}")
        
    except KeyError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        await browser.close()
```

### Retry Logic

```python
async def task_with_retry(task_description: str, max_retries: int = 3):
    browser = AIBrowser()
    await browser.initialize()
    
    for attempt in range(max_retries):
        try:
            result = await browser.execute_task(task_description)
            if result['status'] == 'success':
                return result
            print(f"Attempt {attempt + 1} failed, retrying...")
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
    
    print("All retry attempts failed")
    await browser.close()
```

## 5. Performance Optimization

### Reusing Browser Instance

```python
async def batch_tasks():
    browser = AIBrowser(headless=True)
    await browser.initialize()
    
    try:
        # All tasks use the same browser instance
        tasks = ["Task 1", "Task 2", "Task 3"]
        
        for task in tasks:
            await browser.execute_task(task)
            # Browser state persists between tasks
        
    finally:
        await browser.close()
```

### Disabling Headless Mode for Debugging

```python
# See what the browser is doing
browser = AIBrowser(headless=False)  # Browser window will be visible

# Add slowdown for observation
browser = AIBrowser(headless=False, browser_slow_mo=500)  # 500ms delay
```

### Parallel Task Execution (Advanced)

```python
import asyncio

async def execute_parallel_tasks():
    # Create separate browser instances for parallel tasks
    browsers = [
        AIBrowser(ai_provider="openai"),
        AIBrowser(ai_provider="openai")
    ]
    
    try:
        # Initialize all browsers
        await asyncio.gather(*[b.initialize() for b in browsers])
        
        # Execute tasks in parallel
        tasks = [
            browsers[0].execute_task("Search for Python books"),
            browsers[1].execute_task("Search for Java books")
        ]
        results = await asyncio.gather(*tasks)
        
        print(results)
        
    finally:
        # Close all browsers
        await asyncio.gather(*[b.close() for b in browsers])
```

## 6. Debugging

### Viewing Task History

```python
browser = AIBrowser()
await browser.initialize()

# Execute tasks...

# View recent tasks
history = browser.get_task_history(limit=5)
for task in history:
    print(f"[{task['status']}] {task['description']}")
    print(f"  Result: {task['result']}")
```

### Checking Memory

```python
# Get all saved context
context = browser.memory.get_all_context()
print("Saved Context:", context)

# Get interactions for a task
interactions = browser.memory.get_interactions_for_task(task_id=1)
for interaction in interactions:
    print(f"{interaction['type']}: {interaction['data']}")
```

### Enabling Verbose Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

browser = AIBrowser()
await browser.initialize()
# Now you'll see detailed debug output
```

### Taking Screenshots for Debugging

```python
# Within a task, you can tell AI to take screenshots
browser.save_context("debug_mode", True)

await browser.execute_task(
    "Navigate to the website and take a screenshot of the page"
)
```

## Best Practices

1. **Always cleanup**: Use try/finally to ensure `await browser.close()`
2. **Use context**: Save important data with `save_context()` for persistence
3. **Handle errors**: Check `result['status']` and handle failures
4. **Monitor usage**: Keep an eye on API calls and rate limits
5. **Test locally**: Run with `headless=False` to verify behavior
6. **Document tasks**: Use clear, specific task descriptions
7. **Review history**: Check task history to understand what happened

## Common Patterns

### Authentication Pattern
```python
browser.save_context("credentials", {"username": "...", "password": "..."})
await browser.execute_task("Log in with saved credentials")
```

### Data Scraping Pattern
```python
await browser.execute_task("Navigate to site and collect product data")
data = browser.get_context("collected_data")
```

### Workflow Pattern
```python
for step in workflow_steps:
    result = await browser.execute_task(step)
    if result['status'] != 'success':
        print(f"Workflow failed at: {step}")
        break
```
