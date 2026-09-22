"""
Demo 4: Full Tool Loop with Trace — all 3 tools, step-by-step, with cost

THE POINT OF THIS DEMO: every tool call is a decision you can replay and
a bill you can read. If you cannot trace it, do not ship it. The trace is
your audit log — who was asked, what ran, what it returned, what it cost.

Each query runs through run_tool_loop_with_trace(): decide → execute →
answer, with per-step token usage. Watch how the model CHAINS tools across
rounds, and how every round is another LLM call (and another bill).

Run: python scripts/week-04/demo-04-full-trace.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tools import MAX_TOOL_TURNS, run_tool_loop_with_trace

BORDER = "=" * 70


def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    """Pause so the learner can predict before the reveal."""
    try:
        input(prompt)
    except EOFError:
        print()


def llm_calls_in(trace: dict) -> int:
    """Every trace step that carries 'tokens' corresponds to one LLM call."""
    return sum(1 for s in trace["steps"] if "tokens" in s)


def tokens_of(trace: dict) -> dict:
    return trace.get("usage", {})


print(BORDER)
print("  Demo 4: Full Tool Loop — Trace, Audit, and Cost")
print(BORDER)
print()
print("  The trace is the audit log: who decided, what executed, what it")
print("  returned — and how many tokens each decision cost.")
print()

queries = [
    "Is the auth-service healthy?",
    "What were the last 2 deployments for payment-api?",
    "Is payment-api healthy, what was deployed recently, and are there active incidents?",
]

print("  ⏸  PAUSE & PREDICT: for the last question — how many LLM calls")
print("     do you expect it to take? Guess, then continue.")
pause()
print()

grand = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0}

for query in queries:
    print(f"  QUERY: {query}")
    trace = run_tool_loop_with_trace(query, temperature=0.0)
    print()

    for step in trace["steps"]:
        if step["type"] == "decide":
            t = step.get("tokens", {})
            print(f"    [DECIDE]   in={t.get('input_tokens', 0):>5} out={t.get('output_tokens', 0):>4} tok")
            print(f"              {step['content']}")
        elif step["type"] == "execute":
            print(f"    [EXECUTE]  {step['tool']}")
            try:
                result_data = json.loads(step["result"])
                print(f"              → {json.dumps(result_data)[:130]}")
            except Exception:
                print(f"              → {step['result']}")
        elif step["type"] == "answer":
            t = step.get("tokens", {})
            print(f"    [ANSWER]   in={t.get('input_tokens', 0):>5} out={t.get('output_tokens', 0):>4} tok")
            print(f"              {step['content']}")

    usage = tokens_of(trace)
    calls = llm_calls_in(trace)
    print()
    print(f"    → {calls} LLM call(s);  {usage.get('input_tokens', 0):,} in / "
          f"{usage.get('output_tokens', 0):,} out / {usage.get('total_tokens', 0):,} total tokens")
    print()
    grand["input_tokens"] += usage.get("input_tokens", 0)
    grand["output_tokens"] += usage.get("output_tokens", 0)
    grand["total_tokens"] += usage.get("total_tokens", 0)
    grand["calls"] += calls

print(BORDER)
print("  THE MESSAGE: the trace is your audit log. If you cannot trace a")
print("  decision — replay who decided, what executed, what it returned —")
print("  you should not ship it. And because each round is another LLM")
print("  call, the loop is bounded: a model that never stops calling tools")
print("  is a cost event, not a feature.")
print()
print(f"  This run: {grand['calls']} LLM calls, {grand['total_tokens']:,} total tokens.")
print(f"  The loop is capped at MAX_TOOL_TURNS={MAX_TOOL_TURNS} per query.")
print()
print("  YOUR TURN:")
print("    • Multiply {grand} tokens by your model's per-token price and see")
print("      what one chained answer costs at scale (1,000 users × this).")
print("    • Raise a query whose answer needs NO tool and compare the bill.")
print(BORDER)
