"""
Demo 0: MCP Tradeoffs — From My Tools to Our Tools

THE MESSAGE OF THE WEEK: Week 4 gave the model hands — your tools, wired
directly into your application. But if every team builds the same tools
differently, you get 5 copies of get_build_status in 5 different formats.
MCP standardises this: write a tool once, expose it on a server, and any
client in any language consumes it. This is the shift from "my DevBuddy
has tools" to "our org has a tool ecosystem."

This demo is print-only (no network, runs instantly). It frames the pros,
cons, and the judgment call: when is MCP the right abstraction — and when
is it the wrong one?

Run: python scripts/week-05/demo-00-tradeoffs.py
"""
BORDER = "=" * 70

print(BORDER)
print("  Demo 0: MCP Tradeoffs — From My Tools to Our Tools")
print(BORDER)
print()

print("  THE PROBLEM")
print("  ~~~~~~~~~~~")
print("  Week 4 gave DevBuddy tools. Powerful.")
print("  But what happens when the next team needs get_build_status?")
print("  They write it again. Different format. Different error handling.")
print("  Now you have 5 copies of the same tool in 5 different codebases.")
print("  This is the new copy-paste anti-pattern.")
print()

print("  THE SOLUTION: MCP")
print("  ~~~~~~~~~~~~~~~~~")
print("  Model Context Protocol — an open standard.")
print()
print("  ┌──────────────────┐     ┌──────────────────┐     ┌─────┐")
print("  │   MCP Server     │ ←── │   MCP Client     │ ←── │ LLM │")
print("  │  (your tools)    │     │  (DevBuddy)      │     │     │")
print("  └──────────────────┘     └──────────────────┘     └─────┘")
print()
print("  Server: holds the tools. Runs your logic. Exposes them.")
print("  Client: connects, discovers tools, routes model requests.")
print("  Protocol: standard JSON-RPC. Any language. Any platform.")
print()

print("  WHAT CHANGED FROM WEEK 4")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~")
print("  Week 4:  tools are imported — tightly coupled, private to your project")
print("  Week 5:  tools are discovered — loosely coupled, shared across teams")
print()
print("  The SAME tool interface. The SAME data. Just served over a protocol")
print("  that any client can consume — not just your DevBuddy.")
print()

print("  PROS — why you stand up an MCP server")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  • WRITE ONCE. One team writes get_build_status. Every team uses it.")
print("  • DISCOVERABLE. Clients ask 'what tools exist?' — no hardcoded lists.")
print("  • LANGUAGE-AGNOSTIC. Python server, Node.js client. Works the same.")
print("  • SWAPPABLE. Change the server URL; the client doesn't notice.")
print("  • AUDITABLE. Every tool call goes through a shared, logged boundary.")
print()

print("  CONS — the cost of abstraction")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  • LATENCY. Network hop adds 5–50ms per call. stdio is faster than SSE.")
print("  • INFRASTRUCTURE. A server to run. A port to manage. A process to monitor.")
print("  • CONNECTION SURFACE. Wrong port? Wrong transport? Server down?")
print("  • SECURITY BOUNDARY. Your tools are now reachable over the network.")
print("  • OVERHEAD for single-consumer tools. If one team uses it, just import it.")
print()

print("  WHEN NOT TO USE MCP")
print("  ~~~~~~~~~~~~~~~~~~~~")
print("  • ONE team, one tool, no sharing → just import it (Week 4 style).")
print("  • The tool must return in <1ms → network hop adds unacceptable latency.")
print("  • You're prototyping → wire the function directly, wrap in MCP later.")
print("  • The tool modifies production data without auth → DO NOT expose via MCP.")
print()

print("  WHERE THE CONTROL LIVES (say this out loud)")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  What tools exist       → the SERVER decides, not the client.")
print("  Whether a call succeeds → my NETWORK and SERVER, not the model.")
print("  Who can call my tools  → my AUTH and RATE LIMITS, not a prompt.")
print("  What's exposed         → my REGISTRY, not the model.")
print("  When not to use it     → no ecosystem = just import it.")
print()

print(BORDER)
print("  Demos 1–5 then show each of these in action:")
print("    1  wire server → client discovers, server serves")
print("    2  cross-language → same tools, any language")
print("    3  break it → connection failures you will ship")
print("    4  security → blast radius, auth, read-only defaults")
print("    5  MCP + LLM → agent doesn't know tools are remote")
print(BORDER)