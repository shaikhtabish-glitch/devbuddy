"""
Demo 2: The Universal Client

THE POINT OF THIS DEMO: A Python client talking to a Node server is trivial.
The real architectural payoff is that a completely generic client—one that
knows NOTHING about DevBuddy or your company—can instantly become an expert
on your systems by connecting to the MCP Server.

We simulate a "dumb" client (like Claude Desktop) connecting, discovering the
Incident Analysis prompt, fetching the SLA resource, and routing it to the LLM.

Run: python scripts/week-05/demo-02-cross-language.py
"""
import os, sys, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession

MCP_URL = "http://127.0.0.1:8000/sse"
BORDER = "=" * 70

def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    try:
        input(prompt)
    except EOFError:
        print()

async def main():
    print(BORDER)
    print("  Demo 2: The Universal Client (Simulating Claude Desktop)")
    print(BORDER)
    print()
    print("  This script represents a commercial AI client. It has zero")
    print("  hardcoded knowledge of 'DevBuddy', 'inventory-service', or tools.")
    print("  Watch it become an expert dynamically.")
    print()

    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("  📡  Connected to Context Server.")
                print()
                
                # 1. Ask what it can do (Prompts)
                print("  ── 1. Client: 'What workflows do you support?'")
                prompts = await session.list_prompts()
                prompt_name = prompts.prompts[0].name
                print(f"  Server: 'I have a workflow called {prompt_name}'")
                print()
                
                # 2. Execute workflow
                print("  ── 2. Client: 'Let's run it for inventory-service.'")
                prompt_data = await session.get_prompt(prompt_name, {"service_name": "inventory-service"})
                system_instruction = prompt_data.messages[0].content.text if prompt_data.messages else ""
                print(f"  Server gives prompt: '{system_instruction[:60]}...'")
                print()
                
                # 3. Fetch context
                print("  ── 3. Client: 'I need the SLA resource mentioned in the prompt.'")
                resource_data = await session.read_resource("file://shared/data/inventory-service-sla.md")
                sla_text = resource_data.contents[0].text
                print(f"  Server gives resource: '{sla_text.strip()}'")
                print()
                
                # 4. Discover tools
                print("  ── 4. Client: 'What tools can I use to fulfill this?'")
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                print(f"  Server gives tools: {', '.join(tool_names)}")
                print()
                
                print(BORDER)
                print("  THE MESSAGE: The client did no custom integration. It just")
                print("  followed the protocol. If you plug this server into Claude")
                print("  Desktop today, Claude instantly knows how to analyze your")
                print("  incidents using your private SLAs and live data.")
                print("  THAT is the ecosystem payoff.")
                print(BORDER)
                
    except Exception as e:
        print(f"  ❌ Could not connect to MCP server: {e}")
        print("  Make sure it's running: python src/mcp_server.py")

if __name__ == "__main__":
    asyncio.run(main())