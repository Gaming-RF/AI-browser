"""
Test suite for AI Browser

Tests for browser controller, memory manager, DOM helper,
and configuration module.
"""

import asyncio
import os
import pytest
from src.browser.controller import BrowserController
from src.browser.dom_helper import clean_html
from src.memory.manager import MemoryManager
from src.config import Config
from src.agents.base_agent import BaseAIAgent, Message
from src.agents.factory import create_agent


# ═══════════════════════════════════════════════════════════
#  Browser Controller Tests
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_browser_controller_initialization():
    """Test browser controller initialization."""
    controller = BrowserController(headless=True)
    await controller.initialize()

    assert controller.browser is not None
    assert controller.page is not None

    await controller.close()


@pytest.mark.asyncio
async def test_browser_navigation():
    """Test browser navigation."""
    controller = BrowserController(headless=True)
    await controller.initialize()

    await controller.navigate("https://example.com")
    url = await controller.get_url()

    assert "example.com" in url

    await controller.close()


@pytest.mark.asyncio
async def test_browser_viewport():
    """Test browser initializes with custom viewport."""
    controller = BrowserController(
        headless=True,
        viewport_width=800,
        viewport_height=600,
    )
    await controller.initialize()

    size = await controller.page.evaluate(
        "() => ({ w: window.innerWidth, h: window.innerHeight })"
    )
    assert size["w"] == 800
    assert size["h"] == 600

    await controller.close()


@pytest.mark.asyncio
async def test_browser_scroll():
    """Test scroll action."""
    controller = BrowserController(headless=True)
    await controller.initialize()

    await controller.navigate("https://example.com")
    result = await controller.scroll("down", 300)

    assert "Scrolled down" in result
    assert len(controller.action_history) >= 2  # navigate + scroll

    await controller.close()


@pytest.mark.asyncio
async def test_browser_go_back_forward():
    """Test go_back and go_forward."""
    controller = BrowserController(headless=True)
    await controller.initialize()

    await controller.navigate("https://example.com")
    await controller.navigate("https://example.org")

    result_back = await controller.go_back()
    assert "back" in result_back.lower()

    result_fwd = await controller.go_forward()
    assert "forward" in result_fwd.lower()

    await controller.close()


@pytest.mark.asyncio
async def test_browser_action_history():
    """Test that action history tracks all actions."""
    controller = BrowserController(headless=True)
    await controller.initialize()

    await controller.navigate("https://example.com")
    await controller.scroll("down", 200)

    history = controller.get_action_history()
    assert len(history) == 2
    assert history[0]["action_type"] == "navigate"
    assert history[1]["action_type"] == "scroll"

    controller.clear_history()
    assert len(controller.get_action_history()) == 0

    await controller.close()


# ═══════════════════════════════════════════════════════════
#  DOM Helper Tests
# ═══════════════════════════════════════════════════════════

def test_dom_cleaning_strips_scripts():
    """Test that scripts and styles are stripped from HTML."""
    html = """
    <html>
    <head><script>alert('x')</script><style>body{}</style></head>
    <body>
        <h1>Hello World</h1>
        <a href="/about" id="link-about">About Us</a>
        <button id="btn-submit">Submit</button>
        <input type="text" name="query" placeholder="Search..." />
    </body>
    </html>
    """
    result = clean_html(html)

    # Scripts and styles should be gone
    assert "alert" not in result
    assert "body{}" not in result

    # Interactive elements should be listed
    assert "INTERACTIVE ELEMENTS:" in result
    assert "About Us" in result
    assert "Submit" in result
    assert 'placeholder="Search..."' in result

    # Page text should include visible content
    assert "Hello World" in result


def test_dom_cleaning_assigns_selectors():
    """Test that interactive elements get selectors."""
    html = """
    <body>
        <a href="/home" id="nav-home">Home</a>
        <input name="email" type="email" />
    </body>
    """
    result = clean_html(html)

    assert '#nav-home' in result
    assert 'input[name="email"]' in result


def test_dom_cleaning_truncation():
    """Test that long page text is truncated."""
    long_text = "x " * 20000
    html = f"<body><p>{long_text}</p></body>"
    result = clean_html(html, max_length=500)

    assert "truncated" in result.lower()


def test_dom_cleaning_empty_html():
    """Test handling of empty HTML."""
    result = clean_html("")
    assert "INTERACTIVE ELEMENTS:" in result
    assert "(none found)" in result


# ═══════════════════════════════════════════════════════════
#  Memory Manager Tests
# ═══════════════════════════════════════════════════════════

def test_memory_manager():
    """Test memory manager operations."""
    db_path = "test_memory.db"
    memory = MemoryManager(db_path)

    try:
        # Log a task
        task_id = memory.log_task("Test task", {"metadata": "value"})
        assert task_id is not None

        # Update task
        memory.update_task(task_id, "completed", "Task result")

        # Get history
        history = memory.get_task_history()
        assert len(history) > 0
        assert history[0]["status"] == "completed"

        # Save and retrieve context
        memory.save_context("test_key", {"test": "value"})
        context = memory.get_context("test_key")
        assert context == {"test": "value"}

        # Log and retrieve interactions
        memory.log_interaction("test_action", {"action": "click"}, task_id)
        interactions = memory.get_interactions_for_task(task_id)
        assert len(interactions) == 1
        assert interactions[0]["data"]["action"] == "click"

        # Get all context
        all_ctx = memory.get_all_context()
        assert "test_key" in all_ctx

    finally:
        # Cleanup
        memory.clear_memory()
        if os.path.exists(db_path):
            os.remove(db_path)


# ═══════════════════════════════════════════════════════════
#  Config Tests
# ═══════════════════════════════════════════════════════════

def test_config_to_dict():
    """Test that Config.to_dict returns all expected keys."""
    cfg = Config.to_dict()

    expected_keys = {
        "ai_provider", "ai_model", "api_base_url",
        "headless_mode", "browser_slow_mo",
        "viewport_width", "viewport_height",
        "memory_db_path", "max_steps", "task_timeout",
        "max_retries", "vision_mode",
    }
    assert expected_keys.issubset(set(cfg.keys()))


def test_config_defaults():
    """Test that default config values are sensible."""
    assert Config.MAX_STEPS > 0
    assert Config.TASK_TIMEOUT > 0
    assert Config.VIEWPORT_WIDTH > 0
    assert Config.VIEWPORT_HEIGHT > 0


def test_config_local_model_validation():
    """Test that validation passes when API_BASE_URL is set (local model)."""
    original = Config.API_BASE_URL
    try:
        Config.API_BASE_URL = "http://localhost:11434/v1"
        # Should NOT raise even if no API key is set
        Config.validate()
    finally:
        Config.API_BASE_URL = original


# ═══════════════════════════════════════════════════════════
#  Agent Tests
# ═══════════════════════════════════════════════════════════

def test_message_dataclass():
    """Test Message dataclass."""
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_factory_unknown_provider():
    """Test factory raises on unknown provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        create_agent("nonexistent")


def test_factory_error_message_suggests_local():
    """Test that the unknown-provider error message mentions local models."""
    try:
        create_agent("invalid_provider")
    except ValueError as e:
        assert "local" in str(e).lower()


@pytest.mark.asyncio
async def test_execute_ai_actions_nested_json():
    """Test that _execute_ai_actions can correctly parse nested JSON."""
    from src.core import AIBrowser
    
    # Instantiate with a dummy local api_base_url so it doesn't fail on missing OpenAI API key
    browser = AIBrowser(ai_provider="openai", api_base_url="http://localhost:1234/v1")
    
    # Nested JSON response format
    response = 'Some explanation before\n{"action": "save_context", "params": {"key": "username", "value": "alice"}}\nsome text after'
    result = await browser._execute_ai_actions(response)
    
    assert result["success"] is True
    assert result["action"] == "save_context"
    assert browser.get_context("username") == "alice"
    
    # Cleanup memory
    browser.memory.clear_memory()


def test_anthropic_agent_initialization():
    """Test that AnthropicAgent can be initialized successfully."""
    from src.agents.anthropic_agent import AnthropicAgent
    
    agent = AnthropicAgent(api_key="test-api-key")
    assert agent is not None
    assert agent.api_key == "test-api-key"


if __name__ == "__main__":
    print("Run tests with: pytest tests/ -v")
