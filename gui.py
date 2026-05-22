import asyncio
import json
import threading
import customtkinter as ctk
from src.core import AIBrowser
from src.config import Config

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AIBrowserApp(ctk.CTk):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.browser_task = None
        self.browser_instance = None
        
        self.title("AI Browser - Autonomous Agent")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL (Settings) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="⚙️ Settings", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Provider
        self.provider_label = ctk.CTkLabel(self.sidebar_frame, text="AI Provider:")
        self.provider_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.provider_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["openai", "anthropic"])
        self.provider_optionemenu.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Model
        self.model_label = ctk.CTkLabel(self.sidebar_frame, text="Model Name:")
        self.model_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.model_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="e.g. gpt-4o")
        self.model_entry.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Base URL
        self.url_label = ctk.CTkLabel(self.sidebar_frame, text="API Base URL (Optional):")
        self.url_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        self.url_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="http://localhost:11434/v1")
        self.url_entry.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Headless Toggle
        self.headless_switch = ctk.CTkSwitch(self.sidebar_frame, text="Headless Mode (Hidden)")
        self.headless_switch.grid(row=7, column=0, padx=20, pady=(10, 20), sticky="w")
        
        # --- MAIN PANEL (Task & Logs) ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # Task Input
        self.task_label = ctk.CTkLabel(self.main_frame, text="Enter your task:", font=ctk.CTkFont(size=16, weight="bold"))
        self.task_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        
        self.task_textbox = ctk.CTkTextbox(self.main_frame, height=80)
        self.task_textbox.grid(row=1, column=0, pady=(0, 15), sticky="nsew")
        
        # Execute Button
        self.action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew")
        self.action_frame.grid_columnconfigure(0, weight=1)
        
        self.run_button = ctk.CTkButton(
            self.action_frame, 
            text="🚀 Launch & Execute", 
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_task,
            height=40
        )
        self.run_button.grid(row=0, column=0, sticky="e")
        
        # Stop Button
        self.stop_button = ctk.CTkButton(
            self.action_frame, 
            text="⏹ Stop", 
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.stop_task,
            height=40,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
        
        # Logs Window
        self.log_label = ctk.CTkLabel(self.main_frame, text="Activity Log:", font=ctk.CTkFont(size=16, weight="bold"))
        self.log_label.grid(row=3, column=0, pady=(15, 5), sticky="w")
        
        self.log_textbox = ctk.CTkTextbox(self.main_frame, activate_scrollbars=True, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.grid(row=4, column=0, sticky="nsew")
        self.log_textbox.configure(state="disabled")

    def _load_config(self):
        """Load default settings from config."""
        cfg = Config.to_dict()
        self.provider_optionemenu.set(cfg.get("ai_provider", "openai"))
        
        if cfg.get("ai_model"):
            self.model_entry.insert(0, cfg["ai_model"])
            
        if cfg.get("api_base_url"):
            self.url_entry.insert(0, cfg["api_base_url"])
            
        if cfg.get("headless_mode", True):
            self.headless_switch.select()
        else:
            self.headless_switch.deselect()

    def log_message(self, message: str, color: str = None):
        """Safely log a message to the textbox."""
        self.log_textbox.configure(state="normal")
        # Currently CTkTextbox doesn't support text tags for coloring natively without diving into tkinter Text widget.
        # So we just append text.
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _on_step_callback(self, info: dict):
        """Callback invoked by AIBrowser on each step."""
        step = info.get("step", "?")
        result = info.get("result", {})
        action = result.get("action", "—")
        success = result.get("success", True)
        detail = result.get("result", "")
        
        status_icon = "✅" if success else "❌"
        msg = f"[Step {step}] {status_icon} {action} -> {str(detail)[:150]}"
        
        # Use after() to safely update GUI from whatever thread or context this fires in
        self.after(0, self.log_message, msg)

    def start_task(self):
        """Initialize browser and start the task execution in asyncio."""
        task_text = self.task_textbox.get("1.0", "end-1c").strip()
        if not task_text:
            self.log_message("⚠️ Error: Please enter a task.")
            return

        # Update UI state
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self.log_message(f"🚀 Starting task: '{task_text}'")
        
        provider = self.provider_optionemenu.get()
        model = self.model_entry.get().strip()
        base_url = self.url_entry.get().strip() or None
        headless = bool(self.headless_switch.get())
        
        # Schedule the execution in the running asyncio loop
        self.browser_task = self.loop.create_task(
            self.run_browser_task(task_text, provider, model, base_url, headless)
        )

    async def run_browser_task(self, task_description, provider, model, base_url, headless):
        """Async wrapper for the browser execution."""
        try:
            self.log_message(f"Initializing AIBrowser (Headless={headless})...")
            self.browser_instance = AIBrowser(
                ai_provider=provider,
                model=model or None,
                api_base_url=base_url,
                headless=headless,
                max_steps=15
            )
            
            self.browser_instance.on_step(self._on_step_callback)
            
            await self.browser_instance.initialize()
            self.log_message("🌐 Browser launched and ready.")
            
            result = await self.browser_instance.execute_task(task_description)
            
            # Print Final Result
            status = result.get("status", "unknown")
            if status == "success":
                self.log_message(f"✨ Task completed! Result: {result.get('result', '')}")
            else:
                self.log_message(f"⚠️ Task ended with status '{status}': {result.get('error') or result.get('result')}")
                
        except asyncio.CancelledError:
            self.log_message("⏹ Task was canceled by user.")
        except Exception as e:
            self.log_message(f"❌ Critical Error: {str(e)}")
        finally:
            if self.browser_instance:
                self.log_message("Closing browser...")
                await self.browser_instance.close()
                self.browser_instance = None
            
            # Reset UI state
            self.run_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.browser_task = None

    def stop_task(self):
        """Cancel the running browser task."""
        if self.browser_task and not self.browser_task.done():
            self.browser_task.cancel()
            self.log_message("Canceling task...")
            self.stop_button.configure(state="disabled")


async def run_tk(app, interval=0.05):
    """Integrates tkinter update cycle into asyncio event loop."""
    try:
        while True:
            app.update()
            await asyncio.sleep(interval)
    except ctk.tkinter.TclError as e:
        if "application has been destroyed" not in str(e):
            raise

async def main():
    loop = asyncio.get_running_loop()
    app = AIBrowserApp(loop)
    
    # Run the tk window
    await run_tk(app)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
