"""
Demo 0: The Context Protocol — Why REST Wasn't Enough

THE MESSAGE OF THE WEEK: Week 4 gave the model hands (tools). But your model 
is still blind. It doesn't know your architecture, your playbooks, or your SLAs.
If you just use MCP to expose tools, you have reinvented REST / JSON-RPC.

MCP stands for Model CONTEXT Protocol. It provides three primitives:
1. Resources (Read data: "Here is our architecture.md")
2. Prompts (Instructions: "Here is how to analyze an incident")
3. Tools (Actions: "Reboot the server")

This demo frames the architectural shift from "a server for my tools" 
to "a Context Server for any AI client."

Run: python scripts/week-05/demo-00-tradeoffs.py
"""
BORDER = "=" * 70

print(BORDER)
print("  Demo 0: The Context Protocol — Why REST Wasn't Enough")
print(BORDER)
print()

print("  THE PROBLEM WITH WEEK 4")
print("  ~~~~~~~~~~~~~~~~~~~~~~~")
print("  In Week 4, you built `get_build_status`. That's a tool (Action).")
print("  But what if the model needs to read `inventory-service-sla.md` to")
print("  know if a 500ms response time is a violation?")
print("  If you only build tools, you have to write a custom tool for EVERY file.")
print("  That is unscalable. You are building bespoke endpoints for static data.")
print()

print("  THE ARCHITECTURAL SHIFT: RESOURCES & PROMPTS")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  MCP is not just for tools. It exposes your org's CONTEXT.")
print()
print("  1. RESOURCES (The 'Read' primitive)")
print("     Expose files, database tables, or live logs. The client navigates")
print("     them like a filesystem. You don't write custom tools to read them.")
print()
print("  2. PROMPTS (The 'Instruction' primitive)")
print("     Expose standardized workflows. Instead of hardcoding prompts in")
print("     your client code, the server tells the client: 'Here is our")
print("     standard Incident Analysis prompt template.'")
print()
print("  3. TOOLS (The 'Write/Action' primitive)")
print("     What you built in Week 4. Modifying state or triggering workflows.")
print()

print("  THE TRUE PAYOFF: THE UNIVERSAL CLIENT")
print("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("  If MCP was just JSON-RPC, you'd only connect your custom DevBuddy to it.")
print("  But because it standardizes Context, you can plug your MCP server into")
print("  Claude Desktop, Cursor, or Zed TODAY.")
print("  Instantly, commercial AI tools understand your proprietary architecture")
print("  and can execute your custom tools, with ZERO integration code.")
print()

print(BORDER)
print("  The following demos rewrite Week 5 to focus on CONTEXT:")
print("    1  Resources & Prompts → The missing pillars of MCP")
print("    2  The Universal Client → Discovering context without hardcoding")
print("    3  Protocol Errors → Debugging resource and tool failures")
print("    4  Security Scope → The blast radius of exposing raw files")
print("    5  The Ecosystem Payoff → LLM uses Prompts, Resources, and Tools")
print(BORDER)