"""
Demo 1: Tool Call — Wire a tool, watch the model call it

THE POINT OF THIS DEMO is not that the model called a function — it is
that the model could NOT have run it. It returned a request
({name, args}); your code did the work. The model proposes.
Your code disposes.

Walks the loop by hand against the real tool in src.tools:
bind → ask → see the request → execute it yourself → inject → answer.
If the model answers directly without a tool call, the demo says so —
no crash, and the loop still holds.

Run: python scripts/week-04/demo-01-tool-call.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.messages import HumanMessage, ToolMessage

from src.tools import execute_tool_safely, get_build_status
from src.llm import get_llm

BORDER = "=" * 70

print(BORDER)
print("  Demo 1: Wire a Tool → Watch the Model Call It")
print(BORDER)
print()

# ── Step 1: Bind the tool (imported from src.tools — one source of truth) ──
print("  ── Step 1: Bind the tool ───────────────────────────────────")
print()
print("  The model sees get_build_status as a schema — a description of a")
print("  function it MAY ask for. It never sees the implementation.")
print()
llm = get_llm(temperature=0.0)
llm_with_tools = llm.bind_tools([get_build_status])

# ── Step 2: Ask a question that needs the tool ───────────────────
question = "Is the payment-api healthy?"
print("  ── Step 2: Ask ─────────────────────────────────────────────")
print(f"  User: {question}")
print()
print("  ⏸  PAUSE & PREDICT: the model can answer from training data OR")
print("     call the tool for live data. Which will it do?")
try:
    input("  ⏸  Press Enter to see what it decided… ")
except EOFError:
    print()
print()

response = llm_with_tools.invoke([HumanMessage(content=question)])

if not response.tool_calls:
    print("  Model answered directly — no tool call this time:")
    print(f"  {response.content}")
    print()
    print("  That is a routing decision too: the model judged it did not need")
    print("  live data. Ask again with a service name and watch it flip.")
    print()
else:
    # ── Step 3: See the request ────────────────────────────────────
    tc = response.tool_calls[0]
    print("  ── Step 3: See the request ───────────────────────────────")
    print(f"  Model decided to call: {tc['name']}")
    print(f"  With arguments:         {tc['args']}")
    print("  That is ALL the model produced — a request, not an action.")
    print()

    # ── Step 4: YOUR code executes it (app layer) ─────────────────
    print("  ── Step 4: Your code executes it ─────────────────────────")
    print("  The request goes through execute_tool_safely() — the app layer,")
    print("  not the model, decides whether it runs.")
    print()
    result = execute_tool_safely(tc)
    print(f"  Tool returned: {result}")
    print()

    # ── Step 5: Inject the result, get the answer ─────────────────
    print("  ── Step 5: Inject result → final answer ──────────────────")
    messages = [
        HumanMessage(content=question),
        response,
        ToolMessage(content=result, tool_call_id=tc["id"]),
    ]
    final = llm_with_tools.invoke(messages)
    print(f"  Model: {final.content}")
    print()

print(BORDER)
print("  The loop: Request → Decide → Execute → Return → Answer")
print("  THE BOUNDARY: the model could NOT have run get_build_status.")
print("  It returned a request. Your code executed it. You decide whether")
print("  a request becomes an action — and you keep the trace.")
print("  The model proposes. Your code disposes.")
print(BORDER)
