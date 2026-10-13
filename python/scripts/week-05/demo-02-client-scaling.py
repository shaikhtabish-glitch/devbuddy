"""
Demo 2: Advanced Client Patterns (Real Implementation)

THE POINT OF THIS DEMO: 
We don't just simulate Progressive Tool Discovery—we actually build it.
The LLM starts with only ONE tool (`search_tools`).
When it searches, our client intercepts the search, queries the MCP server's 
cached tool list, dynamically converts the matched MCP JSON schemas into 
LangChain tools, binds them to the LLM on the fly, and resumes the loop.

Run: python scripts/week-05/demo-02-client-scaling.py
"""
import os, sys, asyncio, json
from pydantic import BaseModel, Field, create_model

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool, tool
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
    print("  Demo 2: Real Progressive Tool Discovery (Client Scaling)")
    print(BORDER)
    print()

    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("  [CLIENT] Synchronizing tool registry from Context Server...")
            mcp_tools = (await session.list_tools()).tools
            print(f"  [CLIENT] Discovered {len(mcp_tools)} tools. (Imagine this is 10,000 tools in an enterprise).")
            print("  [CLIENT] ⚠️ Loading 10,000 JSON schemas would cost ~1.5M tokens per request.")
            print("  [CLIENT] 🛡️ Strategy: Starting LLM with ONLY ONE tool -> 'search_tools'.")
            print()
            await asyncio.sleep(1)

            active_lc_tools = []
            
            @tool
            def search_tools(query: str) -> str:
                """Search for available tools on the server and automatically load their schemas."""
                print(f"\n  [CLIENT] Intercepted LLM request to search cache for: '{query}'")
                query_words = query.lower().split()
                matches = []
                for t in mcp_tools:
                    name_desc = (t.name + " " + (t.description or "")).lower()
                    if any(w in name_desc for w in query_words):
                        matches.append(t)
                
                if not matches:
                    return "No tools found matching your query."
                
                names = []
                for mt in matches:
                    if any(t.name == mt.name for t in active_lc_tools):
                        continue
                        
                    args_schema = _mcp_schema_to_pydantic(mt.name, mt.inputSchema or {})
                    
                    async def make_mcp_call(mt_name=mt.name, **kwargs):
                        print(f"\n  [CLIENT] Passing tool execution to Server: {mt_name}({kwargs})")
                        res = await session.call_tool(mt_name, kwargs)
                        return res.content[0].text if res.content else "Success"
                    
                    st = StructuredTool(
                        name=mt.name, 
                        description=mt.description or mt.name,
                        args_schema=args_schema, 
                        func=lambda **kw: "Sync execution not supported",
                        coroutine=make_mcp_call
                    )
                    active_lc_tools.append(st)
                    names.append(mt.name)
                    
                    # Print the schema injection for visual proof!
                    print(f"  [CLIENT] 💉 DYNAMIC INJECTION: Binding schema for '{mt.name}' to LLM context:")
                    print("  " + "-"*50)
                    for line in json.dumps(mt.inputSchema, indent=2).split('\n'):
                        print(f"  {line}")
                    print("  " + "-"*50)
                
                return f"Found and loaded schemas for: {names}. You can now call them directly in your next turn."

            active_lc_tools.append(search_tools)
            llm = get_llm(temperature=0)
            
            messages = [
                SystemMessage(content="You are an agent. You start with NO domain tools loaded. You MUST use `search_tools` to find what you need. After searching, the schemas will be loaded and you can call them."),
                HumanMessage(content="What is the build status of the payment-api?")
            ]
            
            print("  [INPUT]: What is the build status of the payment-api?")
            print("  ── LLM Orchestration Loop (Turn 1) ─────────────────")
            await asyncio.sleep(1)
            
            for turn in range(1, 6):
                if turn > 1:
                    print(f"  ── LLM Orchestration Loop (Turn {turn}) ─────────────────")
                
                bound_llm = llm.bind_tools(active_lc_tools)
                
                print("  [LLM] Thinking...")
                response = await bound_llm.ainvoke(messages)
                messages.append(response)
                
                if not response.tool_calls:
                    print(f"\n  [OUTPUT]: {response.content}")
                    break
                
                for tc in response.tool_calls:
                    print(f"  [LLM] Decided to use tool: {tc['name']}({tc['args']})")
                    tool_obj = next(t for t in active_lc_tools if t.name == tc['name'])
                    
                    if tc['name'] == 'search_tools':
                        res = tool_obj.invoke(tc['args'])
                    else:
                        res = await tool_obj.coroutine(**tc['args'])
                        print(f"  [SERVER] Result: {res.strip()}")
                        
                    messages.append(ToolMessage(content=str(res), tool_call_id=tc["id"]))
                print()
                await asyncio.sleep(1.5)

            print()
            print(BORDER)
            print("  THE PAYOFF: We just proved that an AI can navigate an infinitely")
            print("  large API surface by dynamically searching, discovering, and")
            print("  binding heavy JSON schemas to itself AT RUNTIME, saving millions")
            print("  of tokens per request.")
            print(BORDER)

if __name__ == "__main__":
    asyncio.run(main())