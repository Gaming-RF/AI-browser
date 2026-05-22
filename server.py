"""
AI Browser — Web Server

FastAPI server with WebSocket for real-time browser agent interaction.
Replaces the old CustomTkinter GUI with a modern web-based chat interface.

Run:
    python server.py
    Open http://localhost:8000 in your browser
"""

import asyncio
import json
import os
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

from src.core import AIBrowser
from src.memory.manager import MemoryManager

# ── App Setup ──────────────────────────────────────────────
app = FastAPI(title="AI Browser Agent")

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared memory instance (for history queries outside of tasks)
_memory = MemoryManager("memory.db")


# ── Background Data Aggregator ─────────────────────────────

async def deal_scraper_task():
    """Periodically fetches game deals and caches them in memory.db."""
    import httpx
    while True:
        try:
            print("[Data Aggregator] Fetching fresh game deals...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://www.gamerpower.com/api/giveaways")
                if resp.status_code == 200:
                    deals = resp.json()
                    _memory.save_deals(deals)
                    print(f"[Data Aggregator] Successfully cached {len(deals)} deals.")
                else:
                    print(f"[Data Aggregator] Failed to fetch deals. HTTP {resp.status_code}")
        except Exception as e:
            print(f"[Data Aggregator] Error scraping deals: {e}")
            
        # Wait 15 minutes before checking again
        await asyncio.sleep(15 * 60)

@app.on_event("startup")
async def startup_event():
    # Start the background data aggregator when the server starts
    asyncio.create_task(deal_scraper_task())


# ── Routes ─────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main web UI."""
    html_path = STATIC_DIR / "index.html"
    return FileResponse(str(html_path))


@app.get("/api/models")
async def get_models():
    """Return available models, including auto-detected Ollama models."""
    ollama_models = []
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    ollama_models.append({
                        "name": m.get("name", ""),
                        "size": m.get("size", 0),
                        "modified": m.get("modified_at", ""),
                    })
    except Exception:
        pass  # Ollama not running — that's fine

    return {
        "ollama": ollama_models,
        "cloud": {
            "openai": ["gpt-4o", "gpt-4", "gpt-4o-mini", "gpt-3.5-turbo"],
            "anthropic": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "gemini": [
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ]
        },
    }


@app.get("/api/history")
async def get_history():
    """Return recent task history."""
    history = _memory.get_task_history(20)
    return {"history": history}

class WorkflowData(BaseModel):
    events: List[Dict[str, Any]]
    url: str

@app.post("/api/record_workflow")
async def record_workflow(data: WorkflowData):
    """Save a recorded workflow to memory.db."""
    try:
        # Save the workflow under a generic task name, or we can prompt the user later.
        # For now, we just save it as a "Recorded Workflow"
        _memory.save_task(
            description=f"Recorded Workflow on {data.url}",
            status="completed",
            steps=len(data.events),
            error=None
        )
        return {"status": "success", "events_saved": len(data.events)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class ImportDataRequest(BaseModel):
    browser: str
    types: List[str]

@app.post("/api/import_browser_data")
async def import_browser_data(req: ImportDataRequest):
    """Extract and decrypt browser data using DPAPI."""
    try:
        from src.browser.importer import BrowserImporter
        importer = BrowserImporter(target_browser=req.browser)
        results = {}
        
        if "passwords" in req.types:
            results["passwords"] = importer.extract_passwords()
        if "cookies" in req.types:
            results["cookies"] = importer.extract_cookies()
            
        return {"status": "success", "results": results}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/games/free")
async def get_free_games():
    """Return free games from the local SQLite cache instantly."""
    try:
        deals = _memory.get_deals()
        return {
            "status": "success", 
            "source": "cache",
            "games": deals
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class SystemLimitRequest(BaseModel):
    pid: int
    action: str  # 'limit_cpu', 'suspend', 'resume', 'normal'

@app.post("/api/system/limit")
async def apply_system_limit(req: SystemLimitRequest):
    """Apply native OS-level restrictions to an Electron renderer process."""
    try:
        import psutil
        proc = psutil.Process(req.pid)
        
        if req.action == "limit_cpu":
            # Lower priority to minimum so background processes yield to the OS
            if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):
                proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            elif hasattr(psutil, "IDLE_PRIORITY_CLASS"):
                proc.nice(psutil.IDLE_PRIORITY_CLASS)
            else:
                proc.nice(10) # Unix nice value
            return {"status": "success", "action": "limit_cpu", "pid": req.pid}
            
        elif req.action == "normal":
            # Restore normal priority
            if hasattr(psutil, "NORMAL_PRIORITY_CLASS"):
                proc.nice(psutil.NORMAL_PRIORITY_CLASS)
            else:
                proc.nice(0)
            return {"status": "success", "action": "normal", "pid": req.pid}
            
        elif req.action == "suspend":
            # Physically freeze the process in RAM (Drops CPU to 0.0%)
            proc.suspend()
            return {"status": "success", "action": "suspend", "pid": req.pid}
            
        elif req.action == "resume":
            # Unfreeze the process
            proc.resume()
            return {"status": "success", "action": "resume", "pid": req.pid}
            
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid action"})
            
    except Exception as e:
        print(f"[System Limiter] Failed to apply {req.action} to PID {req.pid}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── WebSocket ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket handler for real-time agent communication."""
    await ws.accept()

    browser_instance: Optional[AIBrowser] = None
    task_handle: Optional[asyncio.Task] = None

    async def send_json(data: dict):
        """Send a JSON message to the client, ignoring errors."""
        try:
            await ws.send_json(data)
        except Exception:
            pass

    async def on_step_callback(info: dict):
        """Called by AIBrowser at each step — streams updates to the client."""
        msg_type = info.get("type", "step")

        if msg_type == "thinking":
            await send_json({
                "type": "thinking",
                "step": info.get("step"),
            })
            return

        # Regular step
        result = info.get("result", {})
        await send_json({
            "type": "step",
            "step": info.get("step"),
            "ai_response": info.get("ai_response", ""),
            "result": result,
            "screenshot": info.get("screenshot"),
        })

    async def run_task(task_text: str, config: dict):
        """Execute a browser task and stream results."""
        nonlocal browser_instance

        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-4")
        base_url = config.get("base_url")
        api_key = config.get("api_key")
        headless = config.get("headless", True)
        vision_mode = config.get("vision_mode", False)
        max_steps = config.get("max_steps", 15)

        try:
            browser_instance = AIBrowser(
                ai_provider=provider,
                model=model,
                api_key=api_key,
                api_base_url=base_url,
                headless=headless,
                memory_db="memory.db",
                max_steps=max_steps,
                vision_mode=vision_mode,
            )

            # Register async callback for real-time updates
            browser_instance.on_step_async(on_step_callback)

            await browser_instance.initialize()

            result = await browser_instance.execute_task(task_text)

            # Send final result
            status = result.get("status", "unknown")
            if status == "success":
                await send_json({
                    "type": "completed",
                    "result": result.get("result", ""),
                    "steps": result.get("steps"),
                    "task_id": result.get("task_id"),
                })
            elif status == "cancelled":
                await send_json({"type": "cancelled"})
            elif status == "max_steps_reached":
                await send_json({
                    "type": "max_steps",
                    "steps": result.get("steps"),
                    "result": result.get("result", ""),
                })
            else:
                await send_json({
                    "type": "error",
                    "error": result.get("error", "Task failed."),
                    "steps": result.get("steps"),
                })

        except asyncio.CancelledError:
            await send_json({"type": "cancelled"})
        except Exception as e:
            await send_json({
                "type": "error",
                "error": str(e),
            })
        finally:
            if browser_instance:
                try:
                    await browser_instance.close()
                except Exception:
                    pass
                browser_instance = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "start_task":
                # Cancel any existing task
                if task_handle and not task_handle.done():
                    if browser_instance:
                        browser_instance.cancel()
                    task_handle.cancel()
                    try:
                        await task_handle
                    except (asyncio.CancelledError, Exception):
                        pass

                # Start new task
                task_text = data.get("task", "").strip()
                if not task_text:
                    await send_json({
                        "type": "error",
                        "error": "No task provided.",
                    })
                    continue

                config = {
                    "provider": data.get("provider", "openai"),
                    "model": data.get("model", "gpt-4"),
                    "base_url": data.get("base_url"),
                    "api_key": data.get("api_key"),
                    "headless": data.get("headless", True),
                    "vision_mode": data.get("vision_mode", False),
                    "max_steps": data.get("max_steps", 15),
                }

                task_handle = asyncio.create_task(run_task(task_text, config))

            elif msg_type == "stop":
                if browser_instance:
                    browser_instance.cancel()
                if task_handle and not task_handle.done():
                    task_handle.cancel()

            elif msg_type == "redirect":
                if browser_instance:
                    new_msg = data.get("message", "")
                    if new_msg:
                        browser_instance.redirect(new_msg)

    except WebSocketDisconnect:
        # Clean up on disconnect
        if browser_instance:
            browser_instance.cancel()
        if task_handle and not task_handle.done():
            task_handle.cancel()
            try:
                await task_handle
            except (asyncio.CancelledError, Exception):
                pass


# ── Entry Point ────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    # Fix Windows console encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    def start():
        """Start the FastAPI server."""
        port = 8000
        
        print("\n  [AI Browser Agent]")
        print("  =======================================")
        print(f"  Server starting on http://localhost:{port}")
        print("  Open this URL in your browser to start.\n")
        
        # Run server
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    start()
