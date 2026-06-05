"""
AI Browser Quick Start Guide

This module provides a simple entry point to get started with AI Browser.
Supports cloud providers (OpenAI, Anthropic) and local models (Ollama, LM Studio).
"""

import asyncio
import sys
from src.core import AIBrowser
from src.config import Config


# ── ANSI Colours ───────────────────────────────────────────
class _C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE   = "\033[94m"


def _step_callback(info: dict):
    """Print step-by-step progress in real time."""
    step   = info.get("step", "?")
    result = info.get("result", {})
    action = result.get("action", "—")
    success = result.get("success", True)
    detail = result.get("result", "")

    icon = f"{_C.GREEN}✔{_C.RESET}" if success else f"{_C.RED}✘{_C.RESET}"
    print(
        f"  {_C.DIM}step {step}{_C.RESET}  "
        f"{icon}  {_C.CYAN}{action}{_C.RESET}  "
        f"{_C.DIM}{str(detail)[:120]}{_C.RESET}"
    )


async def main():
    """Main entry point."""
    print(f"\n{_C.BOLD}{_C.CYAN}🤖 AI Browser — Autonomous Task Executor{_C.RESET}")
    print(f"{_C.DIM}{'═' * 52}{_C.RESET}\n")

    # ── Configuration summary ──────────────────────────────
    cfg = Config.to_dict()
    provider  = cfg["ai_provider"]
    model     = cfg["ai_model"]
    base_url  = cfg["api_base_url"]
    vision    = cfg["vision_mode"]
    max_steps = cfg["max_steps"]

    print(f"  {_C.BOLD}Provider:{_C.RESET}   {provider}")
    print(f"  {_C.BOLD}Model:{_C.RESET}      {model}")
    if base_url:
        print(f"  {_C.BOLD}Endpoint:{_C.RESET}   {base_url}  {_C.YELLOW}(local){_C.RESET}")
    print(f"  {_C.BOLD}Vision:{_C.RESET}     {'enabled' if vision else 'disabled'}")
    print(f"  {_C.BOLD}Max steps:{_C.RESET}  {max_steps}")
    print()

    # ── Override provider / model interactively ────────────
    override = input(
        f"  Use these settings? {_C.DIM}[Y/n]{_C.RESET} "
    ).strip().lower()

    if override == "n":
        provider = input(
            f"\n  {_C.BOLD}AI provider{_C.RESET} (openai/anthropic) "
            f"[{provider}]: "
        ).strip() or provider
        model = input(
            f"  {_C.BOLD}Model{_C.RESET} [{model}]: "
        ).strip() or model
        base_url = input(
            f"  {_C.BOLD}API base URL{_C.RESET} (blank for cloud) "
            f"[{base_url or ''}]: "
        ).strip() or base_url

    # ── Task ───────────────────────────────────────────────
    task = input(f"\n  {_C.BOLD}Enter your task:{_C.RESET} ").strip()
    if not task:
        print(f"{_C.YELLOW}No task provided. Exiting.{_C.RESET}")
        return

    # ── Initialize ─────────────────────────────────────────
    print(f"\n{_C.MAGENTA}🚀 Launching browser …{_C.RESET}")
    browser = AIBrowser(
        ai_provider=provider,
        model=model,
        api_base_url=base_url or None,
        headless=cfg["headless_mode"],
        memory_db=cfg["memory_db_path"],
        max_steps=max_steps,
        vision_mode=vision,
        viewport_width=cfg["viewport_width"],
        viewport_height=cfg["viewport_height"],
    )

    try:
        await browser.initialize()
        print(f"{_C.GREEN}✅ Browser ready.{_C.RESET}\n")

        # Register progress callback
        browser.on_step(_step_callback)

        # ── Execute task ───────────────────────────────────
        print(f"{_C.BOLD}📋 Task:{_C.RESET} {task}")
        print(f"{_C.DIM}{'─' * 52}{_C.RESET}")

        result = await browser.execute_task(task)

        # ── Report ─────────────────────────────────────────
        print(f"{_C.DIM}{'─' * 52}{_C.RESET}")
        status = result.get("status", "unknown")
        steps  = result.get("steps", "?")

        if status == "success":
            print(f"{_C.GREEN}✨ Task completed in {steps} step(s).{_C.RESET}")
            print(f"   {_C.BOLD}Result:{_C.RESET} {result.get('result', '—')}")
        elif status == "max_steps_reached":
            print(f"{_C.YELLOW}⚠  Step limit reached ({steps} steps).{_C.RESET}")
            print(f"   {result.get('result', '')}")
        else:
            print(f"{_C.RED}❌ Task failed after {steps} step(s).{_C.RESET}")
            print(f"   {result.get('error', '—')}")

        # ── Recent history ─────────────────────────────────
        print(f"\n{_C.BOLD}📚 Recent Tasks:{_C.RESET}")
        history = browser.get_task_history(5)
        for h in history:
            s_icon = {"completed": "✔", "failed": "✘", "running": "…"}.get(
                h["status"], "?"
            )
            print(f"   {s_icon}  {h['description'][:60]}  [{h['status']}]")

    except KeyboardInterrupt:
        print(f"\n{_C.YELLOW}⏹  Interrupted by user.{_C.RESET}")
    except Exception as e:
        print(f"{_C.RED}❌ Error: {e}{_C.RESET}")
    finally:
        await browser.close()
        print(f"\n{_C.DIM}👋 Browser closed.{_C.RESET}")


if __name__ == "__main__":
    asyncio.run(main())
