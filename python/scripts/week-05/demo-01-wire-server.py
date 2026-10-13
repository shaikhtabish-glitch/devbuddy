"""
Demo 1: Discovering Context (Resources & Prompts)

THE POINT OF THIS DEMO: We are going to connect to the MCP server and ask it
for Context, not just Tools. We will discover the shared markdown documents
(Resources) and standard operational templates (Prompts).

Prerequisites:
  MCP server running in another terminal:
    python src/mcp_server.py

Run: python scripts/week-05/demo-01-wire-server.py
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
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(BORDER)
            print("  Demo 1: Discovering Context (Resources & Prompts)")
            print(BORDER)
            print()

            # ── Step 1: Discover Resources ─────────────────────────
            print("  ── Step 1: Discover Resources ─────────────────────")
            print("  Instead of writing a custom tool to read the SLA document,")
            print("  the server exposes it as a standard Resource.")
            print()
            
            resources_result = await session.list_resources()
            templates_result = await session.list_resource_templates()
            total = len(resources_result.resources) + len(templates_result.resourceTemplates)
            print(f"  Server exposes {total} resource(s) / template(s):")
            
            for r in resources_result.resources:
                print(f"    • [Static] {r.name} (URI: {r.uri})")
            for t in templates_result.resourceTemplates:
                print(f"    • [Template] {t.name} (URI: {t.uriTemplate})")
            print()
            
            print("  ⏸  Let's read a resource directly via the protocol.")
            pause()
            
            # Read a resource
            target_uri = "file://shared/data/inventory-service-sla.md"
            print(f"  Reading: {target_uri}")
            try:
                resource_data = await session.read_resource(target_uri)
                text = resource_data.contents[0].text
                print("  Contents:")
                print(f"    {text.strip()}")
            except Exception as e:
                print(f"  ❌ Error reading resource: {e}")
            print()

            # ── Step 2: Discover Prompts ───────────────────────────
            print("  ── Step 2: Discover Prompts ───────────────────────")
            print("  The server also holds the standard playbook for incident analysis.")
            print("  The client doesn't need to hardcode the prompt.")
            print()
            
            prompts_result = await session.list_prompts()
            print(f"  Server exposes {len(prompts_result.prompts)} prompt(s):")
            for p in prompts_result.prompts:
                desc = p.description or "(no description)"
                args = [arg.name for arg in (p.arguments or [])]
                print(f"    • {p.name}: {desc}")
                print(f"      Args: {', '.join(args) if args else 'None'}")
            print()
            
            print("  ⏸  Let's fetch the prompt template for 'auth-service'.")
            pause()
            
            try:
                prompt_data = await session.get_prompt("incident_analysis_prompt", {"service_name": "auth-service"})
                print("  Returned Prompt Message:")
                print(f"    {prompt_data.description}")
                for msg in prompt_data.messages:
                    if msg.content.type == "text":
                        print(f"    Content: {msg.content.text[:80]}...")
            except Exception as e:
                print(f"  ❌ Error fetching prompt: {e}")
            print()
            
            print(BORDER)
            print("  THE SHIFT: Your client just read a proprietary document and")
            print("  fetched an operational workflow without calling a single 'tool'.")
            print("  This is Context Engineering.")
            print(BORDER)

if __name__ == "__main__":
    asyncio.run(main())