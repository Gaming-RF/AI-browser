"""
Browser Control Module

Handles all browser automation and interaction via Playwright.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json


@dataclass
class BrowserAction:
    """Represents a browser action to be performed."""
    action_type: str  # "navigate", "click", "type", "screenshot", etc.
    selector: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "selector": self.selector,
            "text": self.text,
            "url": self.url,
            "metadata": self.metadata or {}
        }


class BrowserController:
    """Controls browser actions using Playwright."""

    def __init__(
        self,
        headless: bool = True,
        slow_mo: int = 0,
        viewport_width: int = 1280,
        viewport_height: int = 900,
    ):
        """
        Initialize the browser controller.

        Args:
            headless: Run browser in headless mode
            slow_mo: Slow down actions by this many milliseconds
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.browser = None
        self.page = None
        self.playwright = None
        self.action_history: List[BrowserAction] = []

    async def initialize(self):
        """Initialize the browser."""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            # Find the active tab
            active_page = None
            fallback_page = None
            
            for context in self.browser.contexts:
                for p in context.pages:
                    url = p.url
                    if "browser.html" not in url and not url.startswith("devtools://"):
                        if not fallback_page:
                            fallback_page = p
                        try:
                            # Check if Electron marked this tab as active
                            is_active = await p.evaluate('window.__isActiveTab')
                            if is_active:
                                active_page = p
                                break
                        except Exception:
                            pass
                if active_page:
                    break
                    
            self.page = active_page or fallback_page
            
            if not self.page:
                for p in self.browser.contexts[0].pages:
                    if "browser.html" not in p.url and not p.url.startswith("devtools://"):
                        self.page = p
                        break
                        
            # Absolute fallback if somehow still none
            if not self.page:
                self.page = self.browser.contexts[0].pages[0]
                
        except Exception as e:
            print(f"Could not connect to Electron CDP (is the app running?): {e}")
            # Fallback to launching a fresh headless browser
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
            )
            self.page = await self.browser.new_page(
                viewport={
                    "width": self.viewport_width,
                    "height": self.viewport_height,
                }
            )
        
        cursor_script = """
            if (!document.getElementById('ai-virtual-cursor')) {
                const cursor = document.createElement('div');
                cursor.id = 'ai-virtual-cursor';
                cursor.style.width = '20px';
                cursor.style.height = '20px';
                cursor.style.borderRadius = '50%';
                cursor.style.backgroundColor = 'rgba(255, 0, 0, 0.6)';
                cursor.style.border = '2px solid white';
                cursor.style.position = 'fixed';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '999999999';
                cursor.style.transition = 'transform 0.1s ease-out, background-color 0.1s';
                cursor.style.transform = 'translate(-50%, -50%)';
                cursor.style.top = '0';
                cursor.style.left = '0';
                cursor.style.boxShadow = '0 2px 5px rgba(0,0,0,0.3)';
                document.documentElement.appendChild(cursor);

                document.addEventListener('mousemove', (e) => {
                    cursor.style.left = e.clientX + 'px';
                    cursor.style.top = e.clientY + 'px';
                });
                document.addEventListener('mousedown', () => {
                    cursor.style.backgroundColor = 'rgba(0, 255, 0, 0.6)';
                    cursor.style.transform = 'translate(-50%, -50%) scale(0.8)';
                });
                document.addEventListener('mouseup', () => {
                    cursor.style.backgroundColor = 'rgba(255, 0, 0, 0.6)';
                    cursor.style.transform = 'translate(-50%, -50%) scale(1)';
                });
            }
        """
        
        # Inject virtual cursor for future navigations
        await self.page.add_init_script(cursor_script)
        
        # Inject immediately into the current page
        try:
            await self.page.evaluate(cursor_script)
        except Exception:
            pass

    # ── Navigation ─────────────────────────────────────────

    async def navigate(self, url: str) -> str:
        """Navigate to a URL."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.goto(url, wait_until="load")
        action = BrowserAction(action_type="navigate", url=url)
        self.action_history.append(action)
        return f"Navigated to {url}"

    async def go_back(self) -> str:
        """Go back in browser history."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.go_back(wait_until="load")
        action = BrowserAction(action_type="go_back")
        self.action_history.append(action)
        return "Navigated back"

    async def go_forward(self) -> str:
        """Go forward in browser history."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.go_forward(wait_until="load")
        action = BrowserAction(action_type="go_forward")
        self.action_history.append(action)
        return "Navigated forward"

    # ── Interaction ────────────────────────────────────────

    async def click(self, selector: str) -> str:
        """Click an element."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.click(selector, timeout=5000, force=True)
        action = BrowserAction(action_type="click", selector=selector)
        self.action_history.append(action)
        return f"Clicked element: {selector}"

    async def hover(self, selector: str) -> str:
        """Hover over an element (useful for dynamic menus)."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.hover(selector)
        action = BrowserAction(action_type="hover", selector=selector)
        self.action_history.append(action)
        return f"Hovered over element: {selector}"

    async def type_text(self, selector: str, text: str) -> str:
        """Type text into an element."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.fill(selector, text, timeout=5000)
        action = BrowserAction(action_type="type", selector=selector, text=text)
        self.action_history.append(action)
        return f"Typed text into {selector}: {text}"

    async def select_option(self, selector: str, value: str) -> str:
        """Select an option from a dropdown."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.select_option(selector, value)
        action = BrowserAction(
            action_type="select_option",
            selector=selector,
            metadata={"value": value},
        )
        self.action_history.append(action)
        return f"Selected option '{value}' in {selector}"

    async def press_key(self, key: str) -> str:
        """Press a keyboard key."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self.page.keyboard.press(key)
        action = BrowserAction(action_type="press_key", metadata={"key": key})
        self.action_history.append(action)
        return f"Pressed key: {key}"

    # ── Scrolling ──────────────────────────────────────────

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        """Scroll the page.

        Args:
            direction: "up" or "down"
            amount: Pixels to scroll
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        delta = amount if direction == "down" else -amount
        await self.page.evaluate(f"window.scrollBy(0, {delta})")
        action = BrowserAction(
            action_type="scroll",
            metadata={"direction": direction, "amount": amount},
        )
        self.action_history.append(action)
        return f"Scrolled {direction} by {amount}px"

    # ── Content Retrieval ──────────────────────────────────

    async def get_content(self) -> str:
        """Get the page content (HTML)."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        content = await self.page.content()
        action = BrowserAction(action_type="get_content")
        self.action_history.append(action)
        return content

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Take a screenshot."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        screenshot_bytes = await self.page.screenshot(path=path)
        action = BrowserAction(action_type="screenshot", metadata={"path": path})
        self.action_history.append(action)
        return screenshot_bytes

    async def screenshot_base64(self) -> str:
        """Take a screenshot and return it as a base64-encoded PNG string."""
        import base64

        screenshot_bytes = await self.screenshot()
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    async def get_title(self) -> str:
        """Get the page title."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        title = await self.page.title()
        return title

    async def get_url(self) -> str:
        """Get the current URL."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        return self.page.url

    # ── JavaScript ─────────────────────────────────────────

    async def evaluate_js(self, js_code: str) -> Any:
        """Execute JavaScript in the page."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        result = await self.page.evaluate(js_code)
        action = BrowserAction(
            action_type="evaluate_js",
            metadata={"js_code": js_code},
        )
        self.action_history.append(action)
        return result

    # ── Waiting ────────────────────────────────────────────

    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for an element to appear."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    # ── Lifecycle ──────────────────────────────────────────

    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # ── History ────────────────────────────────────────────

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get the action history."""
        return [action.to_dict() for action in self.action_history]

    def clear_history(self):
        """Clear the action history."""
        self.action_history = []
