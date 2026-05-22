"""
Main Orchestrator

Central component that coordinates the browser, AI agent, and memory system.
Supports autonomous multi-step task execution with self-correction.
"""

import asyncio
import json
import re
from typing import Optional, Dict, Any, List, Callable, Awaitable
from src.agents.factory import create_agent
from src.browser.controller import BrowserController
from src.browser.dom_helper import clean_html
from src.memory.manager import MemoryManager


class AIBrowser:
    """Main orchestrator for the AI Browser system."""

    def __init__(
        self,
        ai_provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        headless: bool = True,
        memory_db: str = "memory.db",
        max_steps: int = 15,
        vision_mode: bool = False,
        viewport_width: int = 1280,
        viewport_height: int = 900,
    ):
        """
        Initialize the AI Browser.

        Args:
            ai_provider: AI provider ("openai" or "anthropic").
                         For local models use "openai" with api_base_url.
            model: Model identifier (e.g. "gpt-4", "llama3", "mistral")
            api_key: API key (optional for local models)
            api_base_url: Custom endpoint (e.g. http://localhost:11434/v1)
            headless: Run browser in headless mode
            memory_db: Path to memory database
            max_steps: Maximum autonomous steps per task
            vision_mode: Send screenshots to the model at each step
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
        """
        self.ai_provider = ai_provider
        self.ai_agent = create_agent(ai_provider, model, api_key, api_base_url)
        self.browser = BrowserController(
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )
        self.memory = MemoryManager(memory_db)
        self.max_steps = max_steps
        self.vision_mode = vision_mode
        self.current_task_id: Optional[int] = None

        # Callbacks for real-time progress reporting
        self._on_step: Optional[callable] = None
        self._on_step_async: Optional[Callable[..., Awaitable]] = None

        # Cancellation and redirection
        self._cancelled = False
        self._redirect_message: Optional[str] = None

    def on_step(self, callback: callable):
        """Register a synchronous callback that fires after every autonomous step.

        The callback receives a dict with keys:
            step, action, params, result, reasoning, status
        """
        self._on_step = callback

    def on_step_async(self, callback: Callable[..., Awaitable]):
        """Register an async callback that fires after every autonomous step.

        The callback receives a dict with keys:
            step, ai_response, result, screenshot
        """
        self._on_step_async = callback

    def cancel(self):
        """Request cancellation of the currently running task."""
        self._cancelled = True

    def redirect(self, new_instruction: str):
        """Inject a new instruction that overrides the current task mid-loop."""
        self._redirect_message = new_instruction

    async def initialize(self):
        """Initialize all components."""
        await self.browser.initialize()
        print(f"AI Browser initialized with {self.ai_provider} provider")

    # ── Public API ─────────────────────────────────────────

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task autonomously using the AI agent.

        The agent runs in a loop — observing the page, deciding an action,
        executing it, and repeating — until it declares the task complete
        or the step limit is reached.

        Args:
            task_description: Natural language description of the task

        Returns:
            Result dictionary with status and details
        """
        # Reset cancellation / redirect state
        self._cancelled = False
        self._redirect_message = None

        # Log the task
        self.current_task_id = self.memory.log_task(task_description)
        self.memory.update_task(self.current_task_id, "running")

        # Clear agent conversation history for a fresh task
        self.ai_agent.clear_history()

        step = 0
        last_action_result: Optional[str] = None
        active_task = task_description

        try:
            while step < self.max_steps:
                # ── Check cancellation ─────────────────────
                if self._cancelled:
                    self.memory.update_task(
                        self.current_task_id, "cancelled",
                        "Task cancelled by user",
                    )
                    return {
                        "status": "cancelled",
                        "task_id": self.current_task_id,
                        "steps": step,
                        "result": "Task was cancelled by user.",
                    }

                # ── Check redirect ─────────────────────────
                if self._redirect_message:
                    active_task = self._redirect_message
                    self._redirect_message = None
                    last_action_result = json.dumps({
                        "notice": "User has redirected you with a new instruction.",
                        "new_task": active_task,
                    })

                step += 1

                # ── 1. Observe ─────────────────────────────
                context = await self._get_current_context()

                # ── 2. Build prompt ────────────────────────
                prompt = self._build_prompt(
                    active_task, context, step, last_action_result,
                )

                # ── 3. Optionally capture screenshot for AI ─
                screenshot_for_ai = None
                if self.vision_mode:
                    try:
                        screenshot_for_ai = await self.browser.screenshot()
                    except Exception:
                        screenshot_for_ai = None

                # ── 4. Notify: thinking ────────────────────
                if self._on_step_async:
                    await self._on_step_async({
                        "type": "thinking",
                        "step": step,
                    })

                # ── 5. Get AI decision ─────────────────────
                ai_response = await self.ai_agent.send_message(
                    prompt, image_data=screenshot_for_ai,
                )

                # ── 6. Parse and execute ───────────────────
                result = await self._execute_ai_actions(ai_response)

                # ── 7. Always capture screenshot for UI ────
                screenshot_b64 = None
                try:
                    if self.browser.page:
                        screenshot_b64 = await self.browser.screenshot_base64()
                except Exception:
                    screenshot_b64 = None

                # ── 8. Fire progress callbacks ─────────────
                step_info = {
                    "step": step,
                    "ai_response": ai_response,
                    "result": result,
                    "screenshot": screenshot_b64,
                }

                if self._on_step:
                    self._on_step(step_info)

                if self._on_step_async:
                    await self._on_step_async({
                        "type": "step",
                        **step_info,
                    })

                # ── 9. Check completion ────────────────────
                if result.get("completed"):
                    self.memory.update_task(
                        self.current_task_id, "completed",
                        json.dumps(result),
                    )
                    return {
                        "status": "success",
                        "task_id": self.current_task_id,
                        "steps": step,
                        "result": result.get("result"),
                    }

                # Feed the action outcome back for the next iteration
                last_action_result = json.dumps(result, default=str)

            # Step limit reached
            self.memory.update_task(
                self.current_task_id, "completed",
                f"Reached max steps ({self.max_steps})",
            )
            return {
                "status": "max_steps_reached",
                "task_id": self.current_task_id,
                "steps": step,
                "result": f"Task did not complete within {self.max_steps} steps.",
            }

        except asyncio.CancelledError:
            self.memory.update_task(
                self.current_task_id, "cancelled", "Task cancelled",
            )
            return {
                "status": "cancelled",
                "task_id": self.current_task_id,
                "steps": step,
                "result": "Task was cancelled.",
            }

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.memory.update_task(self.current_task_id, "failed", error_msg)
            return {
                "status": "failed",
                "task_id": self.current_task_id,
                "steps": step,
                "error": error_msg,
            }

    # ── Context Gathering ──────────────────────────────────

    async def _get_current_context(self) -> Dict[str, Any]:
        """Get current browser and memory context."""
        current_url = None
        page_title = None
        page_dom = None

        if self.browser.page:
            try:
                current_url = self.browser.page.url
            except Exception:
                pass
            try:
                page_title = await self.browser.get_title()
            except Exception:
                pass
            try:
                raw_html = await self.browser.get_content()
                page_dom = clean_html(raw_html)
            except Exception:
                page_dom = "(could not read page)"

        context = {
            "current_url": current_url,
            "page_title": page_title,
            "page_dom": page_dom,
            "recent_history": self.memory.get_task_history(5),
            "saved_context": self.memory.get_all_context(),
        }

        return context

    # ── Prompt Engineering ─────────────────────────────────

    def _build_prompt(
        self,
        task_description: str,
        context: Dict,
        step: int,
        last_result: Optional[str],
    ) -> str:
        """Build the prompt for the AI agent."""

        last_result_section = ""
        if last_result:
            last_result_section = f"""
LAST ACTION RESULT (step {step - 1}):
{last_result}
"""

        prompt = f"""You are an intelligent browser automation agent. Your task is to accomplish the following:

TASK: {task_description}

STEP: {step} of {self.max_steps}

CURRENT CONTEXT:
- Current URL: {context['current_url']}
- Page Title: {context['page_title']}
- Saved Information: {json.dumps(context['saved_context'], indent=2)}
{last_result_section}
PAGE STATE:
{context.get('page_dom', '(no page loaded)')}

AVAILABLE ACTIONS:
You can use the following browser actions. Respond with a JSON object containing the action to take:
- navigate(url): Go to a URL
- click(selector): Click an element (use selectors from INTERACTIVE ELEMENTS above)
- type_text(selector, text): Type text into an element
- press_key(key): Press a keyboard key (e.g. "Enter", "Tab", "Escape")
- scroll(direction, amount): Scroll the page ("up" or "down", amount in pixels)
- hover(selector): Hover over an element
- select_option(selector, value): Select a dropdown option
- go_back(): Go back in browser history
- go_forward(): Go forward in browser history
- screenshot(): Take a screenshot
- get_content(): Get page HTML
- evaluate_js(code): Execute JavaScript
- wait_for_selector(selector): Wait for element to appear
- save_context(key, value): Save information for later use

FORMAT YOUR RESPONSE AS A JSON OBJECT:
{{
    "action": "action_name",
    "params": {{"key": "value"}},
    "reasoning": "Why you chose this action",
    "next_steps": "What you plan to do next"
}}

If the task is complete, respond with:
{{"status": "completed", "result": "Summary of what was accomplished"}}

If an action failed, analyze the error and try a different approach.
"""
        return prompt

    # ── Action Execution ───────────────────────────────────

    async def _execute_ai_actions(self, ai_response: str) -> Dict[str, Any]:
        """Parse and execute actions from AI response."""
        try:
            # Try to extract the outermost JSON object from the response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}')
            if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
                return {
                    "error": "No JSON block found in response. You MUST respond with a single valid JSON object.",
                    "success": False
                }

            action_data = json.loads(ai_response[start_idx:end_idx+1])

            # Check if task is completed
            if action_data.get("status") == "completed":
                return {"completed": True, "result": action_data.get("result")}

            # Execute the action
            action = action_data.get("action")
            params = action_data.get("params", {})

            result = await self._execute_action(action, params)

            # Log the interaction
            self.memory.log_interaction(
                "ai_action",
                {
                    "action": action,
                    "params": params,
                    "reasoning": action_data.get("reasoning", ""),
                    "result": str(result),
                },
                self.current_task_id,
            )

            return result

        except json.JSONDecodeError as e:
            return {
                "error": f"JSON parse error: {str(e)}. You MUST respond with a single valid JSON object.",
                "success": False
            }

    async def _execute_action(self, action: str, params: Dict) -> Dict[str, Any]:
        """Execute a browser action."""
        try:
            if action == "navigate":
                result = await self.browser.navigate(params.get("url"))
            elif action == "click":
                result = await self.browser.click(params.get("selector"))
            elif action == "type_text":
                result = await self.browser.type_text(
                    params.get("selector"),
                    params.get("text"),
                )
            elif action == "screenshot":
                await self.browser.screenshot()
                result = "Screenshot captured"
            elif action == "get_content":
                result = await self.browser.get_content()
            elif action == "evaluate_js":
                result = await self.browser.evaluate_js(params.get("code"))
            elif action == "press_key":
                result = await self.browser.press_key(params.get("key"))
            elif action == "wait_for_selector":
                found = await self.browser.wait_for_selector(
                    params.get("selector"),
                )
                result = f"Element {'found' if found else 'not found'}: {params.get('selector')}"
            elif action == "scroll":
                result = await self.browser.scroll(
                    params.get("direction", "down"),
                    int(params.get("amount", 500)),
                )
            elif action == "hover":
                result = await self.browser.hover(params.get("selector"))
            elif action == "select_option":
                result = await self.browser.select_option(
                    params.get("selector"),
                    params.get("value"),
                )
            elif action == "go_back":
                result = await self.browser.go_back()
            elif action == "go_forward":
                result = await self.browser.go_forward()
            elif action == "save_context":
                self.memory.save_context(
                    params.get("key"), params.get("value"),
                )
                result = f"Saved '{params.get('key')}' to context"
            else:
                result = f"Unknown action: {action}"

            return {"action": action, "result": result, "success": True}

        except Exception as e:
            return {
                "action": action,
                "result": f"Action failed: {str(e)}",
                "success": False,
                "error": str(e),
            }

    # ── Lifecycle ──────────────────────────────────────────

    async def close(self):
        """Close the browser and cleanup."""
        await self.browser.close()

    # ── Convenience ────────────────────────────────────────

    def get_task_history(self, limit: int = 10) -> list:
        """Get task history."""
        return self.memory.get_task_history(limit)

    def get_context(self, key: str) -> Optional[Any]:
        """Get a saved context value."""
        return self.memory.get_context(key)

    def save_context(self, key: str, value: Any):
        """Save a context value."""
        self.memory.save_context(key, value)
