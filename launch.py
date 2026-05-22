import asyncio
import sys
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        print("[AI Browser] Launching Chromium browser in non-headless mode (visible)...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        print("[AI Browser] Navigating to Google...")
        await page.goto("https://www.google.com")
        print("\nBrowser launched successfully! You should see a Chromium window open on your screen.")
        print("Press ENTER here (or stop the task) to close the browser session when you are finished.")
        
        # Wait for user input to close
        await asyncio.to_thread(input)
        
        print("Closing browser...")
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBrowser closed.")
