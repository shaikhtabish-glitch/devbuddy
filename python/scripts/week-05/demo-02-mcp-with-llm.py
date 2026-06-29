"""
Demo 2: MCP Tools + LLM — model calls tools via MCP

Connects to the MCP server, discovers tools, describes them to the LLM,
and the LLM decides which tools to call. Tool execution goes through
the MCP session.

Run: python scripts/week-05/demo-02-mcp-with-llm.py
"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import get_llm

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "mcp_server.py")


async def main():
    server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools

            print("=" * 70)
            print("  Demo 2: MCP Tools + LLM — Model Calls Tools via MCP")
            print("=" * 70)
            print()
            print(f"  Discovered {len(tools)} tools from MCP server:")
            for t in tools:
                print(f"    • {t.name}: {t.description.strip().split(chr(10))[0]}")
            print()

            # Build tool descriptions for the system prompt
            tool_descriptions = "\n".join(
                f"- {t.name}: {t.description.strip()}" for t in tools
            )

            question = "Is the payment-api healthy and what were its last 2 deployments?"
            print(f"  Query: {question}")
            print()

            # Step 1: Ask LLM which tool(s) to call
            llm = get_llm(temperature=0)
            plan_response = llm.invoke([
                SystemMessage(content=(
                    "You are an engineering assistant. You have access to these tools:\n\n"
                    f"{tool_descriptions}\n\n"
                    "When asked a question, respond with a JSON array of tool calls to make. "
                    "Each tool call must have 'tool' (the name) and 'args' (a dict of arguments). "
                    "Only respond with the JSON array, nothing else.\n\n"
                    "Example: [{\"tool\": \"get_build_status\", \"args\": {\"service_name\": \"auth-service\"}}]"
                )),
                HumanMessage(content=question),
            ])

            plan_text = plan_response.content.strip()
            # Extract JSON from response
            if "```" in plan_text:
                plan_text = plan_text.split("```")[1]
                if plan_text.startswith("json"):
                    plan_text = plan_text[4:]
            tool_calls = json.loads(plan_text)

            print(f"  LLM decided to call: {json.dumps(tool_calls, indent=2)}")
            print()

            # Step 2: Execute each tool call via MCP session
            results = []
            for tc in tool_calls:
                tool_name = tc["tool"]
                args = tc["args"]
                result = await session.call_tool(tool_name, args)
                result_text = result.content[0].text if result.content else "no result"
                results.append({"tool": tool_name, "args": args, "result": json.loads(result_text)})
                print(f"  → {tool_name}({args})")
                print(f"  ← {json.dumps(json.loads(result_text), indent=2)[:200]}")

            print()

            # Step 3: Ask LLM for final answer using the tool results
            context = json.dumps(results, indent=2)
            final_response = llm.invoke([
                SystemMessage(content=(
                    "You are an engineering assistant. The user asked a question. "
                    "Here are the results from the tools you called. Answer the user's "
                    "question based on this data.\n\n"
                    f"Tool results:\n{context}"
                )),
                HumanMessage(content=question),
            ])

            print(f"  Answer: {final_response.content}")
            print()
            print("=" * 70)
            print("  The full path: Query → LLM plans → MCP executes →")
            print("  Results → LLM answers. No tool binding needed.")
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
