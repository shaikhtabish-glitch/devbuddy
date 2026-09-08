"""
Demo 4: Full Tool Loop with Trace — all 3 tools, step-by-step

THE POINT OF THIS DEMO: every tool call is a decision you can replay and
a bill you can read. If you cannot trace it, do not ship it. The trace is
your audit log — who was asked, what ran, what it returned, what it cost.

Uses run_tool_loop_with_trace() to show the complete
decide → execute → return → answer loop across all three tools.

Run: python scripts/week-04/demo-04-full-trace.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tools import run_tool_loop_with_trace

print("=" * 70)
print("  Demo 4: Full Tool Loop — All 3 Tools with Trace")
print("=" * 70)
print()

queries = [
    "Is the auth-service healthy?",
    "What were the last 2 deployments for payment-api?",
    "Are there any active incidents for inventory-service?",
    "Is payment-api healthy, what was deployed recently, and any incidents?",
]

for query in queries:
    print(f"  QUERY: {query}")
    trace = run_tool_loop_with_trace(query, temperature=0.0)
    print()

    for step in trace["steps"]:
        if step["type"] == "decide":
            print(f"    [DECIDE]  {step['content']}")
        elif step["type"] == "execute":
            print(f"    [EXECUTE] {step['tool']}")
            try:
                result_data = json.loads(step["result"])
                print(f"              → {json.dumps(result_data)[:120]}")
            except Exception:
                print(f"              → {step['result']}")
        elif step["type"] == "answer":
            print(f"    [ANSWER]  {step['content']}")
    print()

print("=" * 70)
print("  Every tool call goes through: Decide → Execute → Answer.")
print("  THE MESSAGE: the trace is your audit log. If you cannot trace a")
print("  decision — replay who decided, what executed, what it returned —")
print("  you should not ship it. And because each round is another LLM")
print("  call, the loop is bounded: a model that never stops calling tools")
print("  is a cost event, not a feature.")
print("=" * 70)
