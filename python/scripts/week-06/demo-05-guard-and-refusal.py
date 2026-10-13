"""
Demo 5 (C3): Guards — the agent knows when to stop

Test 1: guarded chain WITH check_build → guard passes → typed report
Test 2: same query, check_build removed   → guard BLOCKS (typed answer)
Test 3: refusal — "Deploy ..."             → registry-driven refusal

Requires: MCP server (python src/mcp_server.py) + Qdrant (docker-compose up -d)
Test 3 needs only the LLM.
Run: python scripts/week-06/demo-05-guard-and-refusal.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_guarded_chain, run_dynamic_agent, format_report

HEALTHY_QUERY = "Is payment-api healthy?"

print()
print("=" * 65)
print("  Demo 5 (C3): Validity Guard + Structural Refusal")
print("=" * 65)
print()


def show(result, label):
    print(f"  🔀  Path: {' → '.join(m['step'] for m in result['messages'])}")
    print(f"  [state] build_status = {result['build_status']!r}")
    if result["error"]:
        print(f"  🛑  {result['error']}")
    print(f"  {'─' * 59}")
    print(format_report(result["report"]))
    print()


# ── Test 1: guard PASSES when required data is present ────────

print("  ── Test 1: build checked → guard PASSES → report generated ──")
print(f"  📥  QUERY: \"{HEALTHY_QUERY}\"")
show(run_guarded_chain(HEALTHY_QUERY), "pass")


# ── Test 2: guard STOPS when required data is missing ─────────

print("  ── Test 2: check_build REMOVED → guard STOPS the agent ──")
print(f"  📥  QUERY: \"{HEALTHY_QUERY}\"")
show(run_guarded_chain(HEALTHY_QUERY, include_build=False), "block")


# ── Test 3: refusal — no deploy tool exists ───────────────────

print("  ── Test 3: 'Deploy ...' → refused from the registry ──")
DEPLOY_QUERY = "Deploy auth-service to production"
print(f"  📥  QUERY: \"{DEPLOY_QUERY}\"")
show(run_dynamic_agent(DEPLOY_QUERY), "refuse")
print("  The refusal message lists ONLY registry entries — the model")
print("  never got to invent what the agent can do.")
print("=" * 65)
print()