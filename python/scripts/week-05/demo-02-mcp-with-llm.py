"""
Demo 2: MCP Tools + LLM — model decides, MCP executes

Connects to the MCP server, discovers tools, and lets the LLM decide
which tools to call at runtime using LangChain's native tool-calling API.
The LLM receives tool schemas discovered from MCP, decides which to call,
and the MCP session executes them.

This is the same decide → execute → return loop from Week 4, but the
tools are discovered dynamically from the MCP server — not hardcoded.

Run: python scripts/week-05/demo-02-mcp-with-llm.py
"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
from src.llm import get_llm

MCP_URL = "http://127.0.0.1:8000/sse"


def _mcp_schema_to_pydantic(name: str, schema: dict) -> type[BaseModel]:
    """Convert an MCP tool's inputSchema to a Pydantic model for LangChain tool binding."""
    fields = {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        description = prop_info.get("description", "")
        is_required = prop_name in required

        py_type = str
        if prop_type == "integer":
            py_type = int
        elif prop_type == "number":
            py_type = float

        if is_required:
            fields[prop_name] = (py_type, Field(description=description))
        else:
            fields[prop_name] = (py_type | None, Field(default=None, description=description))

    if not fields:
        # Tool has no arguments — use an empty model
        return create_model(f"{name}Args", __base__=BaseModel)

    return create_model(f"{name}Args", **fields)


async def main():
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = (await session.list_tools()).tools

            print("=" * 70)
            print("  Demo 2: MCP Tools + LLM — Decide → Execute → Return")
            print("=" * 70)
            print()
            print(f"  Discovered {len(mcp_tools)} tools from MCP server:")
            for t in mcp_tools:
                desc_line = t.description.strip().split(chr(10))[0] if t.description else "(no description)"
                print(f"    • {t.name}: {desc_line}")
            print()

            # ── Convert MCP tools → LangChain tool definitions ──
            lc_tools = []
            for mt in mcp_tools:
                args_schema = _mcp_schema_to_pydantic(
                    mt.name, mt.inputSchema or {}
                )
                desc_line = mt.description.strip().split("\n")[0] if mt.description else mt.name
                lc_tools.append(StructuredTool(
                    name=mt.name,
                    description=desc_line,
                    args_schema=args_schema,
                    # func is a stub — we never call it directly; MCP session handles execution
                    func=lambda **kwargs: None,
                ))

            question = "Is the payment-api healthy and what were its last 2 deployments?"
            print(f"  Query: {question}")
            print()

            # ── Step 1: LLM decides which tools to call ──────────
            llm = get_llm(temperature=0)
            llm_with_tools = llm.bind_tools(lc_tools)

            decision = llm_with_tools.invoke([
                SystemMessage(content=(
                    "You are an engineering assistant. Use the available tools to "
                    "answer the user's question. Call ALL tools needed to provide "
                    "a complete answer."
                )),
                HumanMessage(content=question),
            ])

            tool_calls = decision.tool_calls or []
            print(f"  LLM decided: {json.dumps([tc for tc in tool_calls], indent=2, default=str)}")
            print()

            # ── Step 2: Execute via MCP session ──────────────────
            results = []
            for tc in tool_calls:
                tool_name = tc["name"]
                args = tc["args"]
                result = await session.call_tool(tool_name, args)
                result_text = result.content[0].text if result.content else "no result"
                results.append({"tool": tool_name, "args": args, "result": result_text})
                print(f"  → {tool_name}({args})")
                print(f"  ← {result_text[:200]}...")
            print()

            # ── Step 3: LLM produces final answer ─────────────────
            # Build message list with original tool_call_ids so
            # the model can correlate results to its own calls.
            messages = [
                SystemMessage(content=(
                    "You are an engineering assistant. Answer the user's question "
                    "using the tool results below. Be concise and accurate."
                )),
                HumanMessage(content=question),
                decision,  # include the AIMessage with tool_calls for id correlation
            ]
            for tc, r in zip(tool_calls, results):
                messages.append(ToolMessage(
                    content=r["result"],
                    tool_call_id=tc["id"],
                    name=r["tool"],
                ))

            final_response = llm.invoke(messages)
            print(f"  Answer: {final_response.content}")
            print()
            print("=" * 70)
            print("  Decide → Execute → Return — same loop as Week 4.")
            print("  Tools discovered dynamically via MCP, not hardcoded.")
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
