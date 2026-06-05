import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from src.browser.controller import BrowserController
from src.browser.dom_helper import clean_html, format_a11y_tree

app = Server("ai-browser-mcp")
browser = None

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available browser automation tools."""
    return [
        types.Tool(
            name="navigate",
            description="Navigate the browser to a specific URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL to navigate to (e.g. https://google.com)"}
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="click",
            description="Click an element on the page using a CSS selector.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click."}
                },
                "required": ["selector"]
            }
        ),
        types.Tool(
            name="type_text",
            description="Type text into an input field.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input element."},
                    "text": {"type": "string", "description": "Text to type."}
                },
                "required": ["selector", "text"]
            }
        ),
        types.Tool(
            name="get_page_snapshot",
            description="Get the current page's semantic Accessibility Tree and Interactive Elements list.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Execute a browser tool."""
    global browser
    if not browser:
        browser = BrowserController()
        await browser.initialize()

    try:
        if name == "navigate":
            result = await browser.navigate(arguments["url"])
            return [types.TextContent(type="text", text=result)]
            
        elif name == "click":
            result = await browser.click(arguments["selector"])
            return [types.TextContent(type="text", text=result)]
            
        elif name == "type_text":
            result = await browser.type_text(arguments["selector"], arguments["text"])
            return [types.TextContent(type="text", text=result)]
            
        elif name == "get_page_snapshot":
            raw_html = await browser.get_content()
            page_dom = clean_html(raw_html)
            
            try:
                raw_a11y = await browser.get_a11y_tree()
                a11y_str = format_a11y_tree(raw_a11y)
                page_dom += "\n\nACCESSIBILITY TREE:\n" + a11y_str
            except Exception:
                pass
                
            return [types.TextContent(type="text", text=page_dom)]
            
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def main():
    """Run the MCP server over stdio."""
    print("Starting AI Browser MCP Server...", flush=True)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
