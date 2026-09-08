"""
Demo 0: Tool Use — the tradeoffs and when NOT to use it

THE MESSAGE OF THE WEEK: Week 3 gave the model a memory — you boxed its
input (retrieval). Week 4 gives it hands — you box its actions (tools).
The model proposes. Your code disposes.

This demo is print-only (no LLM, no network, runs instantly). It frames
the pros, cons, and the judgment call: when is tool calling the right
architecture — and when is it the wrong one?

Run: python scripts/week-04/demo-00-tradeoffs.py
"""
BORDER = "=" * 70

print(BORDER)
print("  Demo 0: Tool Use — Tradeoffs & When NOT to Use It")
print(BORDER)
print()

print("  THE BOUNDARY")
print("  ~~~~~~~~~~~~")
print("  The model never runs your code. It returns a REQUEST ({name, args});")
print("  your application decides whether that request becomes an action.")
print("  Safety never comes from the model — it comes from the boundary")
print("  you draw: whitelist, validation, retry, denial, audit log.")
print()

print("  The loop")
print("  ~~~~~~~~")
print("  Request → Decide (model) → Execute (your code) → Return → Answer")
print("  Every round-trip = another LLM call = latency + tokens.")
print()

print("  PROS — why you wire tools")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  • LIVE data. The model answers from your systems, not stale training.")
print("  • GROUNDED decisions. The answer rests on an executed, checkable result.")
print("  • EXTENSIBLE. Add a capability = add a tool; no prompt surgery.")
print("  • AUDITABLE. Every action is a recorded decision you can replay.")
print()

print("  CONS — what you are really paying")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  • LATENCY. Each tool round adds a full LLM call (seconds, not ms).")
print("  • COST. Tool results re-enter the context; tokens compound per round.")
print("  • A NEW FAILURE SURFACE. Tools crash, time out, return bad data.")
print("  • MISROUTING. The model can pick the wrong tool or skip a needed one.")
print("  • INJECTION SURFACE. A prompt can be tricked into calling a tool with")
print("    hostile args — your whitelist + validation are the only defence.")
print()

print("  WHEN NOT TO USE TOOL CALLING")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  • DETERMINISTIC pipeline (A then B then C every time) → just write code.")
print("  • ONE tool, always the same call → the orchestration overhead isn't")
print("    worth it; call the function directly.")
print("  • The answer must be <100 ms with zero failure modes → do not put an")
print("    LLM in the critical path.")
print()

print("  WHERE THE CONTROL LIVES (say this out loud)")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  Which tool / what args  → model decides; MY descriptions trained it.")
print("  Whether it actually runs → MY whitelist, not the model.")
print("  Retry / denial / fallback→ CODE decisions: deterministic, testable.")
print("  What it cost / did       → MY trace and a bounded loop.")
print("  When not to give it hands→ deterministic paths are just code.")
print()

print(BORDER)
print("  Demos 1–5 then show each of these in action:")
print("    1  wire one tool          → the boundary")
print("    2  route between tools    → descriptions are the design lever")
print("    3  make a tool fail       → retry & denial live in YOUR code")
print("    4  trace the full loop    → audit log + the bill")
print("    5  RAG as a tool          → a tool is just data with a name")
print(BORDER)
