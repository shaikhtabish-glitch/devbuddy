"""
Demo 5: The Ecosystem Payoff — Prompts, Resources, and Tools

THE POINT OF THIS DEMO: The grand finale. The LLM acts as the orchestrator.
It doesn't use hardcoded system prompts. It asks the Server for the Prompt.
It asks the Server for the Resource.
It asks the Server for the Tools.
Then it executes the workflow.

Prerequisites:
  Qdrant running (Week 3)
  MCP server running on port 8000:
    python src/mcp_server.py

Run: python scripts/week-05/demo-05-mcp-with-llm.py
"""
import os, sys, json, asyncio
from pydantic import BaseModel, Field, create_model

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from src.llm import get_llm

MCP_URL = "http://127.0.0.1:8000/sse"
BORDER = "=" * 70

def _mcp_schema_to_pydantic(name: str, schema: dict) -> type[BaseModel]:
    fields = {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        description = prop_info.get("description", "")
        py_type = int if prop_type == "integer" else float if prop_type == "number" else str
        if prop_name in required:
            fields[prop_name] = (py_type, Field(description=description))
        else:
            fields[prop_name] = (py_type | None, Field(default=None, description=description))
    if not fields:
        return create_model(f"{name}Args", __base__=BaseModel)
    return create_model(f"{name}Args", **fields)

async def main():
    print(BORDER)
    print("  Demo 5: The Ecosystem Payoff")
    print(BORDER)
    print()

    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Get Prompt
            print("  ── 1. Fetching Server Prompt ───────────────────────")
            service = "payment-api"
            prompt_data = await session.get_prompt("incident_analysis_prompt", {"service_name": service})
            system_text = prompt_data.messages[0].content.text
            print(f"  Received: '{system_text[:70]}...'")
            print()

            # 2. Get Resource
            print("  ── 2. Fetching Server Resource ─────────────────────")
            try:
                res_data = await session.read_resource("file://shared/data/payment-api-spec.md")
                resource_text = res_data.contents[0].text[:100] + "..."
            except Exception:
                resource_text = "(Resource unavailable)"
            print(f"  Received: '{resource_text}'")
            print()

            # 3. Get Tools
            print("  ── 3. Fetching Server Tools ────────────────────────")
            mcp_tools = (await session.list_tools()).tools
            lc_tools = []
            for mt in mcp_tools:
                args_schema = _mcp_schema_to_pydantic(mt.name, mt.inputSchema or {})
                lc_tools.append(StructuredTool(
                    name=mt.name, description=mt.description or mt.name,
                    args_schema=args_schema, func=lambda **kw: None
                ))
            print(f"  Bound {len(lc_tools)} tools to LLM.")
            print()

            # 4. Execute
            print("  ── 4. LLM Execution Loop ───────────────────────────")
            llm = get_llm(temperature=0).bind_tools(lc_tools)
            
            # The context is assembled purely from the server!
            messages = [
                SystemMessage(content=system_text),
                HumanMessage(content=f"Here is the API Spec Resource: {resource_text}\n\nPlease proceed with the analysis.")
            ]
            
            for turn in range(4):
                response = await llm.ainvoke(messages)
                messages.append(response)
                
                if not response.tool_calls:
                    print(f"  [Final Answer]:\n  {response.content}")
                    break
                    
                for tc in response.tool_calls:
                    print(f"  [Model Decided]: Call {tc['name']}({tc['args']})")
                    result = await session.call_tool(tc["name"], tc["args"])
                    result_text = result.content[0].text if result.content else "no result"
                    messages.append(ToolMessage(content=result_text, tool_call_id=tc["id"]))
            
            print()
            print(BORDER)
            print("  THE MESSAGE: The client is completely generic. The Prompts,")
            print("  Resources, and Tools all lived on the server. We have achieved")
            print("  true separation of Context from the Application layer.")
            print(BORDER)

if __name__ == "__main__":
    asyncio.run(main())