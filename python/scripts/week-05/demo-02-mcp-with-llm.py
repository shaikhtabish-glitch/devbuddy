"""
Demo 2: MCP Tools + LLM — model decides, MCP executes

Connects to the MCP server, discovers tools, and lets the LLM decide
which tools to call at runtime. The LLM produces structured tool-call
decisions (Week 2 pattern), and the MCP session executes them.

This is the same decide → execute → return loop from Week 4, but the
tools are discovered dynamically from the MCP server — not hardcoded.

Run: python scripts/week-05/demo-02-mcp-with-llm.py
"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pydantic import BaseModel, Field
from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import get_llm

MCP_URL = "http://127.0.0.1:8000/sse"


class MCPToolDecision(BaseModel):
    """The LLM's decision about which MCP tools to call. Week 2 pattern."""
    tool_calls: list[dict] = Field(
        description="List of tool calls. Each has 'tool' (name) and 'args' (dict of arguments)."
    )


async def main():
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools

            print("=" * 70)
            print("  Demo 2: MCP Tools + LLM — Decide → Execute → Return")
            print("=" * 70)
            print()
            print(f"  Discovered {len(tools)} tools from MCP server:")
            for t in tools:
                print(f"    • {t.name}: {t.description.strip().split(chr(10))[0]}")
            print()

            # Build tool descriptions for the system prompt
            tool_descriptions = "\n".join(
                f"- {t.name}({t.inputSchema.get('properties', {})}): {t.description.strip()}"
                for t in tools
            )

            question = "Is the payment-api healthy and what were its last 2 deployments?"
            print(f"  Query: {question}")
            print()

            # ── Step 1: LLM decides which tools to call ──────────
            # Uses with_structured_output() — the Week 2 pattern.
            # Safer than json.loads() with markdown hacks.
            llm = get_llm(temperature=0)
            decision_llm = llm.with_structured_output(MCPToolDecision)

            decision = decision_llm.invoke([
                SystemMessage(content=(
                    "You are an engineering assistant. You have access to these tools:\n\n"
                    f"{tool_descriptions}\n\n"
                    "Decide which tools to call and with what arguments. "
                    "Include ALL tools needed to answer the question. "
                    "Use the exact tool names listed above."
                )),
                HumanMessage(content=question),
            ])

            print(f"  LLM decided: {json.dumps(decision.tool_calls, indent=2)}")
            print()

            # ── Step 2: Execute via MCP session ──────────────────
            results = []
            for tc in decision.tool_calls:
                tool_name = tc["tool"]
                args = tc["args"]
                result = await session.call_tool(tool_name, args)
                result_text = result.content[0].text if result.content else "no result"
                results.append({"tool": tool_name, "args": args, "result": result_text})
                print(f"  → {tool_name}({args})")
                print(f"  ← {result_text[:200]}...")
            print()

            # ── Step 3: LLM produces final answer ─────────────────
            context = json.dumps(results, indent=2)
            final_response = llm.invoke([
                SystemMessage(content=(
                    "You are an engineering assistant. Answer the user's question "
                    "using the tool results below. Be concise and accurate.\n\n"
                    f"Tool results:\n{context}"
                )),
                HumanMessage(content=question),
            ])

            print(f"  Answer: {final_response.content}")
            print()
            print("=" * 70)
            print("  Decide → Execute → Return — same loop as Week 4.")
            print("  Tools discovered dynamically via MCP, not hardcoded.")
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
