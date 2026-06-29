"""
Demo 1: MCP Client — Connect, Discover, Call

Connects to the DevBuddy MCP server, lists available tools,
and calls get_build_status for two services.

Run: python scripts/week-05/demo-01-mcp-client.py
(Requires src/mcp_server.py to be importable — no separate server process needed)
"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.stdio import stdio_client
from mcp import ClientSession
from mcp import StdioServerParameters

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "mcp_server.py")

async def main():
    server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: Discover tools
            tools_result = await session.list_tools()
            print("=" * 60)
            print("  Demo 1: MCP Client — Connect, Discover, Call")
            print("=" * 60)
            print()
            print(f"  Available tools:")
            for t in tools_result.tools:
                print(f"    • {t.name}: {t.description}")
            print()

            # Step 2: Call get_build_status
            for service in ["auth-service", "payment-api"]:
                result = await session.call_tool("get_build_status", {"service_name": service})
                print(f"  get_build_status('{service}'):")
                for content in result.content:
                    print(f"    {content.text}")
                print()

            # Step 3: Call get_recent_deploys
            result = await session.call_tool("get_recent_deploys", {"service_name": "payment-api", "limit": 2})
            print(f"  get_recent_deploys('payment-api', limit=2):")
            for content in result.content:
                print(f"    {content.text}")
            print()

            print("=" * 60)
            print("  Client → MCP → Server → Tool → Response")
            print("  Same tools as Week 4. Shared protocol. Any client.")
            print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
