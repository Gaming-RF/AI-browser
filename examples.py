"""
Example Usage of AI Browser

This file demonstrates how to use the AI Browser system with
cloud providers, local models, and advanced features.
"""

import asyncio
from src.core import AIBrowser


# ═══════════════════════════════════════════════════════════
#  Cloud Provider Examples
# ═══════════════════════════════════════════════════════════

async def example_openai():
    """Example using OpenAI (cloud)."""
    browser = AIBrowser(ai_provider="openai", model="gpt-4")

    await browser.initialize()

    try:
        result = await browser.execute_task(
            "Go to Google and search for 'Python programming'"
        )
        print("Task Result:", result)
        print(f"Completed in {result.get('steps', '?')} steps")
    finally:
        await browser.close()


async def example_anthropic():
    """Example using Anthropic (cloud)."""
    browser = AIBrowser(
        ai_provider="anthropic",
        model="claude-3-opus-20240229",
    )

    await browser.initialize()

    try:
        result = await browser.execute_task(
            "Navigate to GitHub and find the top trending Python repositories"
        )
        print("Task Result:", result)
    finally:
        await browser.close()


# ═══════════════════════════════════════════════════════════
#  Local Model Examples
# ═══════════════════════════════════════════════════════════

async def example_ollama():
    """Example using a local model via Ollama."""
    browser = AIBrowser(
        ai_provider="openai",            # uses OpenAI-compatible API
        model="llama3",                   # your local model name
        api_base_url="http://localhost:11434/v1",
        headless=False,                   # show the browser
        max_steps=10,
    )

    await browser.initialize()

    try:
        result = await browser.execute_task(
            "Go to Wikipedia and search for 'artificial intelligence'"
        )
        print("Task Result:", result)
    finally:
        await browser.close()


async def example_lm_studio():
    """Example using a local model via LM Studio."""
    browser = AIBrowser(
        ai_provider="openai",
        model="mistral",
        api_base_url="http://localhost:1234/v1",
        headless=False,
        max_steps=10,
    )

    await browser.initialize()

    try:
        result = await browser.execute_task(
            "Go to Google and search for 'Python tutorials'"
        )
        print("Task Result:", result)
    finally:
        await browser.close()


# ═══════════════════════════════════════════════════════════
#  Vision Mode Example
# ═══════════════════════════════════════════════════════════

async def example_vision():
    """Example with vision mode (requires a vision-capable model)."""
    browser = AIBrowser(
        ai_provider="openai",
        model="gpt-4o",
        vision_mode=True,         # send screenshots at each step
        headless=False,
        max_steps=10,
    )

    await browser.initialize()

    try:
        result = await browser.execute_task(
            "Go to Amazon and find the best-rated laptop under $1000"
        )
        print("Task Result:", result)
    finally:
        await browser.close()


# ═══════════════════════════════════════════════════════════
#  Context and Memory Example
# ═══════════════════════════════════════════════════════════

async def example_with_context():
    """Example with context saving."""
    browser = AIBrowser(ai_provider="openai")

    await browser.initialize()

    try:
        browser.save_context("username", "john_doe")
        browser.save_context("preferences", {"theme": "dark", "language": "en"})

        result = await browser.execute_task(
            "Log in to my account and check my profile"
        )
        print("Task Result:", result)

        username = browser.get_context("username")
        print(f"Saved username: {username}")
    finally:
        await browser.close()


# ═══════════════════════════════════════════════════════════
#  Multi-Step Workflow Example
# ═══════════════════════════════════════════════════════════

async def example_multiple_tasks():
    """Example with multiple sequential tasks."""
    browser = AIBrowser(ai_provider="openai", max_steps=10)

    await browser.initialize()

    try:
        tasks = [
            "Go to Amazon",
            "Search for 'Python books'",
            "Sort by price (low to high)",
            "Take a screenshot of the results",
        ]

        for task in tasks:
            result = await browser.execute_task(task)
            status = result.get("status", "?")
            steps  = result.get("steps", "?")
            print(f"  [{status}] {task}  ({steps} steps)")
    finally:
        await browser.close()


# ═══════════════════════════════════════════════════════════
#  Step Progress Callback Example
# ═══════════════════════════════════════════════════════════

async def example_with_progress():
    """Example showing real-time step progress."""

    def on_step(info):
        step = info["step"]
        r    = info.get("result", {})
        print(f"  → Step {step}: {r.get('action', '?')} → {str(r.get('result', ''))[:80]}")

    browser = AIBrowser(ai_provider="openai", max_steps=10)
    browser.on_step(on_step)

    await browser.initialize()

    try:
        result = await browser.execute_task(
            "Go to google.com and search for 'Playwright Python documentation'"
        )
        print(f"\nFinal: {result}")
    finally:
        await browser.close()


if __name__ == "__main__":
    print("AI Browser Examples")
    print("=" * 55)
    print()
    print("Available examples:")
    print("  1. example_openai()       — OpenAI cloud")
    print("  2. example_anthropic()    — Anthropic cloud")
    print("  3. example_ollama()       — Local model (Ollama)")
    print("  4. example_lm_studio()    — Local model (LM Studio)")
    print("  5. example_vision()       — Vision mode (gpt-4o)")
    print("  6. example_with_context() — Context / memory")
    print("  7. example_multiple_tasks()  — Multi-step workflow")
    print("  8. example_with_progress()   — Step progress callback")
    print()
    print("To run an example:")
    print("  1. Set up your environment (.env or config.yaml)")
    print("  2. Uncomment the example in the block below")
    print("  3. Run: python examples.py")
    print()

    # ── Uncomment one to run ──────────────────────────────
    # asyncio.run(example_openai())
    # asyncio.run(example_anthropic())
    # asyncio.run(example_ollama())
    # asyncio.run(example_lm_studio())
    # asyncio.run(example_vision())
    # asyncio.run(example_with_context())
    # asyncio.run(example_multiple_tasks())
    # asyncio.run(example_with_progress())
