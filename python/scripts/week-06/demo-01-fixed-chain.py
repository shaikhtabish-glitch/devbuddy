"""
Demo 1 (C1): Fixed Chain — a state machine, not a for-loop

build_fixed_chain() compiles nodes + hardcoded edges into a LangGraph
runtime. We STREAM it: the graph drives node → node, and after every
transition you see which state fields the node filled — and which are
still empty (that emptiness is the fuel for C2, demo-04).

Requires: MCP server (python src/mcp_server.py) + Qdrant (docker-compose up -d)
Run: python scripts/week-06/demo-01-fixed-chain.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import build_fixed_chain, _init_state, format_report

DATA_FIELDS = ("service_name", "context", "build_status", "deploys",
               "incidents", "report")


def _empty(value) -> bool:
    return value is None or value == ""


def trace_fixed_chain(query: str):
    """Stream the compiled graph — each event is one node transition."""

    state = _init_state(query)
    print(f"  📥  QUERY: \"{query}\"")
    print(f"  {'─' * 59}")

    agent = build_fixed_chain()   # compile(): nodes + edges → runnable graph
    # edges (hardcoded — THIS is what "fixed" means):
    #   extract_service → retrieve → check_build → report → END

    seen_events = 0
    for event in agent.stream(state):
        for node_name, update in event.items():
            state = {**state, **update}

            node_events = state["messages"][seen_events:]
            seen_events = len(state["messages"])
            filled = [k for k in DATA_FIELDS if not _empty(state[k])]
            pending = [k for k in DATA_FIELDS if _empty(state[k])]

            print(f"  ▶ {node_name}")
            for audit in node_events:
                detail = {k: v for k, v in audit.items() if k not in ("step", "cost")}
                cost = f"  · ${audit['cost']:.6f}" if audit.get("cost") else ""
                print(f"      audit      : {detail}{cost}")
            print(f"      filled     : {', '.join(filled) or '—'}")
            print(f"      still empty: {', '.join(pending) or '—'}"
                  + ("   ← a node that never fills these = C2 (demo-04)"
                     if pending else ""))
            print()

    print(f"  {'─' * 59}")
    print(f"  📤  REPORT (structured AgentAnswer — Week 2 contract):")
    print(format_report(state["report"]))
    print()
    print(f"  🧾  AUDIT TRAIL (recorded by the nodes, with per-step cost):")
    for m in state["messages"]:
        print(f"          • {m}")
    print(f"  ⚡  TOTAL: {state['steps']} steps · ${state['cost']:.6f}")
    print()


# ── Run two queries — same path, every time ────────────────────

print()
print("=" * 65)
print("  Demo 1 (C1): Fixed Chain — the graph drives the transitions")
print("=" * 65)
print()
print("  Nodes are functions. Edges are hardcoded. The RUNTIME walks")
print("  them — nothing below is a hand-written for-loop.")
print()

trace_fixed_chain("Is the payment-api ready for v2.1?")
trace_fixed_chain("Is the auth-service ready for release?")

print("=" * 65)
print("  Fixed chain: same edges, same order, both queries — 4 nodes.")
print("  🔀  extract → retrieve → check_build → report → END")
print("  Predictable and auditable, but it CANNOT skip a step or add")
print("  one (no deploys/incidents nodes here). See demo-02 for a graph")
print("  whose edges are chosen at runtime.")
print("=" * 65)
print()