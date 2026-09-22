"""
Demo 5: MCP + LLM — The Agent Doesn't Know Tools Are Remote

THE POINT OF THIS DEMO: the LLM doesn't care where tools come from.
Hardcoded function? MCP server across the network? It just sees a name,
a description, and argument schemas. The Decide → Execute → Return loop
from Week 4 is IDENTICAL — only the tool source changed.

This is the architectural payoff: the agent orchestrator is transport-
agnostic. You can swap the MCP server URL to a different team's server
and the LLM never notices. Ecosystem achieved.

Prerequisites:
  Qdrant vector DB running:
    docker-compose up -d   (from repo root)

  MCP server running on port 8000:
    python src/mcp_server.py

Run: python scripts/week-05/demo-05-mcp-with-llm.py
"""
import os, sys, json, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
from src.llm import get_llm

MCP_URL = "http://127.0.0.1:8000/sse"
BORDER = "=" * 70
MAX_TOOL_TURNS = 6


def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    try:
        input(prompt)
    except EOFError:
        print()


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
        return create_model(f"{name}Args", __base__=BaseModel)

    return create_model(f"{name}Args", **fields)


def _usage_of(message) -> dict:
    """Best-effort token usage from a LangChain message's usage_metadata."""
    md = getattr(message, "usage_metadata", None) or {}
    return {
        "input_tokens": md.get("input_tokens") or 0,
        "output_tokens": md.get("output_tokens") or 0,
        "total_tokens": md.get("total_tokens") or 0,
    }


async def main():
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ── Step 0: Discover tools from MCP ────────────────────
            mcp_tools = (await session.list_tools()).tools

            print(BORDER)
            print("  Demo 5: MCP + LLM — Agent Doesn't Know Tools Are Remote")
            print(BORDER)
            print()

            print(f"  Discovered {len(mcp_tools)} tools from MCP server:")
            for t in mcp_tools:
                desc_line = t.description.strip().split("\n")[0] if t.description else ""
                print(f"    • {t.name}: {desc_line}")
            print()

            # ── Step 1: Convert MCP tools to LangChain tool defs ───
            print("  ── Step 1: Convert MCP schemas → LangChain tools ───")
            print()
            print("  The MCP server returns JSON schemas. We convert them to")
            print("  Pydantic models and bind them to the LLM as LangChain tools.")
            print("  The LLM never knows these tools came from a network server.")
            print()

            lc_tools = []
            for mt in mcp_tools:
                args_schema = _mcp_schema_to_pydantic(
                    mt.name, mt.inputSchema or {}
                )
                desc = mt.description.strip().split("\n")[0] if mt.description else mt.name
                lc_tools.append(StructuredTool(
                    name=mt.name,
                    description=desc,
                    args_schema=args_schema,
                    func=lambda **kwargs: None,  # stub — MCP session handles execution
                ))
                print(f"      ✅  {mt.name} → LangChain tool")
            print()

            # ── Step 2: LLM decides ────────────────────────────────
            question = "Is the payment-api healthy and what were its last 2 deployments?"
            print(f"  Query: {question}")
            print()
            print("  ⏸  PAUSE & PREDICT: how many tools will the LLM call?")
            print("     One? Two? All three? Guess, then continue.")
            pause()
            print()

            llm = get_llm(temperature=0)
            llm_with_tools = llm.bind_tools(lc_tools)

            messages = [
                SystemMessage(content=(
                    "You are an engineering assistant. Use the available tools to "
                    "answer the user's question. Call ALL tools needed to provide "
                    "a complete answer."
                )),
                HumanMessage(content=question),
            ]

            usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            tool_calls_made = []

            for turn in range(MAX_TOOL_TURNS):
                response = llm_with_tools.invoke(messages)
                messages.append(response)

                usage = _usage_of(response)
                for key in usage_totals:
                    usage_totals[key] += usage.get(key, 0)

                if not response.tool_calls:
                    print(f"  [{turn + 1}] LLM answered directly — no more tools needed")
                    print(f"      {response.content}")
                    print()
                    break

                for tc in response.tool_calls:
                    tool_calls_made.append(tc["name"])
                    print(f"  [{turn + 1}] LLM decided: {tc['name']}({tc['args']})")

                    # ── Step 3: Execute via MCP ────────────────────
                    result = await session.call_tool(tc["name"], tc["args"])
                    result_text = result.content[0].text if result.content else "no result"
                    print(f"      → MCP executed, result received")
                    messages.append(ToolMessage(
                        content=result_text,
                        tool_call_id=tc["id"],
                    ))

            else:
                # The model kept calling tools — force a final answer
                final = llm.invoke(messages)
                print(f"  [forced] MAX_TOOL_TURNS={MAX_TOOL_TURNS} reached — forcing answer")
                print(f"      {final.content}")
                print()

            # ── Step 4: Recap ──────────────────────────────────────
            print("  ── Recap ────────────────────────────────────────────")
            print()
            print(f"  Tools called: {', '.join(tool_calls_made) if tool_calls_made else '(none)'}")
            print(f"  Total tokens: {usage_totals['total_tokens']:,} ({usage_totals['input_tokens']:,} in / {usage_totals['output_tokens']:,} out)")
            print()
            print("  Same loop as Week 4:")
            print("    Decide (LLM) → Execute (MCP) → Return → Answer")
            print()

            print(BORDER)
            print("  THE MESSAGE: The agent orchestrator is transport-agnostic.")
            print("  The LLM doesn't know — and doesn't CARE — whether a tool")
            print("  is a local function or a remote MCP endpoint.")
            print()
            print("  Senior take-home: This is the ecosystem payoff. You can:")
            print("  • Swap the MCP server URL → different team's tools")
            print("  • Add tools to the server → clients discover them")
            print("  • Change server language → protocol remains the same")
            print("  • Move tools between teams → agent doesn't notice")
            print()
            print("  YOUR TURN:")
            print("    • Change MCP_URL to port 3001 (Node.js server).")
            print("      Does the LLM notice? (It should not.)")
            print("    • Add a question that needs ALL THREE tools.")
            print("      Example: 'Summarise auth-service: status, recent")
            print("      deploys, and any active incidents.'")
            print("    • Compare the token cost. Each MCP round is an LLM call.")
            print("      At $0.15/M input and $0.60/M output, what does this")
            print("      question cost at 1,000 users?")
            print(BORDER)


if __name__ == "__main__":
    asyncio.run(main())