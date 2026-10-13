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
import os, sys, re
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

# Structural detection — check claims against STATE, not keywords:
#
# 1) fabricated tool evidence: an evidence chunk citing source='tool'
#    for build data while state['build_status'] is None is a lie the
#    state itself proves.
# 2) affirmative build claims: status words near 'build' — with hedges
#    ("not checked", "no data", "unknown") excluded, because an honest
#    hedge is NOT a hallucination.
# (A naive keyword count would false-positive on "incidents" — it
#  contains "ci" — and would flag honest hedges that mention "build".)

report = result["report"]
fabricated = [
    e.content[:80].replace("\n", " ")
    for e in report.evidence
    if e.source == "tool" and "build" in e.content.lower()
]

haystack = " ".join(
    [report.answer]
    + [e.content for e in report.evidence]
    + (report.verdict.blockers if report.verdict else [])
    + (report.verdict.recommended_next_steps if report.verdict else [])
).lower()

affirmative = re.search(
    r"build[^.\n]{0,60}\b(healthy|passing|green|success\w*|degraded|down|failing|compiled)\b"
    r"|\b(healthy|passing|green|compiled)\b[^.\n]{0,40}build",
    haystack,
)
hedged = re.search(
    r"build[^.\n]{0,60}(not checked|no (build )?data|never (been )?checked|unknown|missing)"
    r"|(not checked|no data|never checked)[^.\n]{0,40}build",
    haystack,
)

detected = bool(fabricated) or bool(affirmative)

print("  🔎  DETECTION (state vs. claims — not keyword counting):")
print(f"      state['build_status']      : None (never checked)")
print(f"      fabricated tool evidence   : {fabricated or 'none'}")
if affirmative:
    print(f"      affirmative build claim    : {affirmative.group(0)!r}")
else:
    print("      affirmative build claim    : none")
if hedged:
    print(f"      hedge present              : {hedged.group(0)!r}")
print()
if detected:
    print("      → HALLUCINATION: the report asserts (or cites tool evidence for)")
    print("        build data that state says was never collected. The model")
    print("        filled a gap YOUR graph left open — it predicts tokens,")
    print("        it doesn't check state.")
else:
    print("      → The model hedged this run (no affirmative claim). The")
    print("        VULNERABILITY is still real: nothing in this graph stops")
    print("        it from inventing. Hedging is luck, not a guardrail.")
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