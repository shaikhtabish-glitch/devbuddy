"""
Demo 5 (C3): Guards — the agent knows when to stop

Test 1: guarded chain WITH check_build → validity guard PASSES → report
Test 2: same query, check_build removed → guard BLOCKS (typed answer,
        zero LLM spend on a report — proven by the cost line)
Test 3: refusal — "Deploy ..." → registry-driven refusal
Test 4: budget guard — MAX_STEPS forced to 2 → run stops with a typed
        answer instead of running away

Requires: MCP server (python src/mcp_server.py) + Qdrant (docker-compose up -d)
Test 3 needs only the LLM.
Run: python scripts/week-06/demo-05-guard-and-refusal.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import src.agent as agent_mod
from src.agent import run_guarded_chain, run_dynamic_agent, format_report

HEALTHY_QUERY = "Is auth-service healthy?"


def show(result) -> dict:
    print(f"  🔀  Path: {' → '.join(m['step'] for m in result['messages'])}")
    print(f"  [state] build_status = {result['build_status']!r}")
    # The guard's DECISION is in the audit — print it, don't infer it.
    for m in result["messages"]:
        if m["step"] == "validate":
            verdict = "🛡  PASS → model may generate the report" \
                if m.get("status") == "passed" \
                else f"🛑 BLOCKED ({m.get('category')})"
            print(f"  {verdict}")
    if result["error"]:
        print(f"  🛑  {result['error']}")
    print(f"  {'─' * 59}")
    print(format_report(result["report"]))
    print(f"  💰  cost so far: ${result['cost']:.6f}")
    print()
    return result


print()
print("=" * 65)
print("  Demo 5 (C3): Validity Guard + Refusal + Budget")
print("=" * 65)
print()
print("  Three guards, three jobs: validity (state must be acceptable),")
print("  structural (registry decides what's possible), budget (steps/cost")
print("  ceiling). All three produce TYPED answers — no LLM, no prose.")
print()

# ── Test 1: validity guard PASSES when required data present ──

print("  ── Test 1: build checked → guard PASSES → report generated ──")
# auth-service: latest deploy success, incident resolved — unambiguous
# ground truth, so this pass-path is stable across runs.
print(f"  📥  QUERY: \"{HEALTHY_QUERY}\"")
r1 = show(run_guarded_chain(HEALTHY_QUERY))


# ── Test 2: validity guard STOPS when required data missing ───

print("  ── Test 2: check_build REMOVED → guard STOPS the agent ──")
print(f"  📥  QUERY: \"{HEALTHY_QUERY}\"")
r2 = show(run_guarded_chain(HEALTHY_QUERY, include_build=False))

path2 = [m["step"] for m in r2["messages"]]
print(f"  💰  COST PROOF: test 1 = ${r1['cost']:.6f}  |  "
      f"test 2 = ${r2['cost']:.6f}")
print(f"      generate_report in test 2's path? "
      f"{'YES (unexpected!)' if 'generate_report' in path2 else 'NO — the guard wrote'}")
print(f"      the blocked answer in CODE. A guard that spends tokens")
print(f"      isn't a guard, it's a suggestion.")
print()


# ── Test 3: refusal — no deploy tool exists ───────────────────

print("  ── Test 3: 'Deploy ...' → refused from the registry ──")
DEPLOY_QUERY = "Deploy auth-service to production"
print(f"  📥  QUERY: \"{DEPLOY_QUERY}\"")
r3 = show(run_dynamic_agent(DEPLOY_QUERY))
for m in r3["messages"]:
    if m["step"] == "plan":
        print(f"  🧠  plan: proposal={m.get('proposal')!r} → {m.get('decision')}"
              f"  ({m.get('reason', 'registry lookup')})")
print("  The refusal message lists ONLY registry entries — the model")
print("  never got to invent what the agent can do.")
print()


# ── Test 4: budget guard — stop a runaway run ─────────────────

print("  ── Test 4: budget guard — MAX_STEPS forced to 2 ──")
BUDGET_QUERY = "Give me a full readiness assessment for payment-api."
print(f"  📥  QUERY: \"{BUDGET_QUERY}\"")
print(f"  🔧  MAX_STEPS: {agent_mod.MAX_STEPS} → 2 (temporarily)")

saved = agent_mod.MAX_STEPS
agent_mod.MAX_STEPS = 2
try:
    r4 = run_dynamic_agent(BUDGET_QUERY)
finally:
    agent_mod.MAX_STEPS = saved

print(f"  🔀  Path: {' → '.join(m['step'] for m in r4['messages'])}")
print(f"  ⚡  Steps: {r4['steps']} (limit was 2)  |  "
      f"next_step={r4['next_step']!r}")
print(f"  {'─' * 59}")
print(format_report(r4["report"]))
print(f"  💰  cost: ${r4['cost']:.6f} — stopped BEFORE burning the budget;")
print(f"      the blocked answer cost 0 tokens (typed, not generated).")
print()
print(f"  🔧  MAX_STEPS restored to {agent_mod.MAX_STEPS}.")
print("=" * 65)
print()