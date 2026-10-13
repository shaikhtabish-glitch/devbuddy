"""
Demo 4 (C2): Missing-Step Hallucination — remove a node, watch it invent

The demo-01 chain with check_build REMOVED and NO guard. The naive report
node renders missing state as '{}' and gives the model no ground rules —
so when BUILD shows up empty, the model completes the report anyway.

Why: the LLM predicts tokens, it doesn't reason about missing data.
This is the SAME mechanism as Week 4's tool-error hallucination.

Requires: MCP server (python src/mcp_server.py) + Qdrant (docker-compose up -d)
Run: python scripts/week-06/demo-04-missing-step.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import (
    run_missing_step_agent, run_guarded_chain, format_report,
)

QUERY = "Is payment-api ready for release?"

print()
print("=" * 65)
print("  Demo 4 (C2): Missing-Step Hallucination")
print("=" * 65)
print()
print("  The check_build node has been REMOVED from the graph.")
print("  state['build_status'] will be None — never checked, no guard.")
print("  Watch what the report does with an empty build status.")
print()

# ── Run the broken graph ───────────────────────────────────────

result = run_missing_step_agent(QUERY)

print(f"  📥  QUERY: \"{QUERY}\"")
print(f"  🔀  Path:  {' → '.join(m['step'] for m in result['messages'])}")
print()
print(f"  [state] build_status = {result['build_status']!r}")
print(f"          → Was the build ever checked? "
      f"{'NO — the node does not exist' if result['build_status'] is None else 'yes'}")
print()

print(f"  {'─' * 59}")
print(f"  📤  NAIVE REPORT (node rendered BUILD: {{}}):")
print(format_report(result["report"]))
print()

# ── Did it invent build data? ──────────────────────────────────

blob = " ".join(
    [result["report"].answer]
    + [e.content for e in result["report"].evidence]
    + (result["report"].verdict.blockers if result["report"].verdict else [])
    + (result["report"].verdict.recommended_next_steps if result["report"].verdict else [])
).lower()
claims = [w for w in ("build", "ci", "passing", "green", "healthy", "compiled")
          if w in blob]

print(f"  🔎  DETECTION:")
print(f"      build_status in state : None (never checked)")
print(f"      report talks about    : {', '.join(claims) if claims else 'NOTHING about the build'}")
if claims:
    print(f"      → HALLUCINATION: the model filled a gap your code left open.")
    print(f"        It didn't 'decide' the build was fine — an empty state")
    print(f"        plus a report-shaped prompt makes invention the most")
    print(f"        probable next token.")
else:
    print(f"      → The model hedged this time. The VULNERABILITY is still")
    print(f"        real: nothing in this graph stops it from inventing.")
    print(f"        Hedging is luck, not a guardrail.")
print()

# ── The same missing step, with the guard attached ─────────────

print("=" * 65)
print("  SAME missing step — now with the C3 validity guard attached")
print("=" * 65)
print()

guarded = run_guarded_chain(QUERY, include_build=False)

print(f"  🔀  Path:  {' → '.join(m['step'] for m in guarded['messages'])}")
print(f"  [state] build_status = {guarded['build_status']!r}")
print(f"  🛑  GUARD: {guarded['error']}")
print()
print(f"  📤  TYPED BLOCKED ANSWER (written by the guard, no LLM):")
print(format_report(guarded["report"]))
print()
print("  The agent REFUSED to produce a confident report from empty state.")
print("  Guard = difference between 'tried its best' and 'knew it couldn't'.")
print("=" * 65)
print()