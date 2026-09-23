/**
 * Demo 0: The Context Protocol — Why REST Wasn't Enough
 *
 * THE MESSAGE OF THE WEEK: Week 4 gave the model hands (tools). But your
 * model is still blind. It doesn't know your architecture, your playbooks,
 * or your SLAs. If you just use MCP to expose tools, you have reinvented
 * REST / JSON-RPC.
 *
 * MCP stands for Model CONTEXT Protocol. It provides three primitives:
 *   1. Resources (Read data: "Here is our architecture.md")
 *   2. Prompts   (Instructions: "Here is how to analyze an incident")
 *   3. Tools     (Actions: "Reboot the server")
 *
 * This demo frames the architectural shift from "a server for my tools"
 * to "a Context Server for any AI client."
 *
 * Run: node scripts/week-05/demo-00-tradeoffs.js
 */
const BORDER = "=".repeat(70);

console.log(BORDER);
console.log("  Demo 0: The Context Protocol — Why REST Wasn't Enough");
console.log(BORDER);
console.log();

console.log("  THE PROBLEM WITH WEEK 4");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  In Week 4, you built `get_build_status`. That's a tool (Action).");
console.log("  But what if the model needs to read `inventory-service-sla.md` to");
console.log("  know if a 500ms response time is a violation?");
console.log("  If you only build tools, you have to write a custom tool for EVERY file.");
console.log("  That is unscalable. You are building bespoke endpoints for static data.");
console.log();

console.log("  THE ARCHITECTURAL SHIFT: RESOURCES & PROMPTS");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  MCP is not just for tools. It exposes your org's CONTEXT.");
console.log();
console.log("  1. RESOURCES (The 'Read' primitive)");
console.log("     Expose files, database tables, or live logs. The client navigates");
console.log("     them like a filesystem. You don't write custom tools to read them.");
console.log();
console.log("  2. PROMPTS (The 'Instruction' primitive)");
console.log("     Expose standardized workflows. Instead of hardcoding prompts in");
console.log("     your client code, the server tells the client: 'Here is our");
console.log("     standard Incident Analysis prompt template.'");
console.log();
console.log("  3. TOOLS (The 'Write/Action' primitive)");
console.log("     What you built in Week 4. Modifying state or triggering workflows.");
console.log();

console.log("  THE TRUE PAYOFF: THE UNIVERSAL CLIENT");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  If MCP was just JSON-RPC, you'd only connect your custom DevBuddy to it.");
console.log("  But because it standardizes Context, you can plug your MCP server into");
console.log("  Claude Desktop, Cursor, or Zed TODAY.");
console.log("  Instantly, commercial AI tools understand your proprietary architecture");
console.log("  and can execute your custom tools, with ZERO integration code.");
console.log();

console.log(BORDER);
console.log("  The following demos rewrite Week 5 to focus on CONTEXT:");
console.log("    1  Resources & Prompts → The missing pillars of MCP");
console.log("    2  The Universal Client → Discovering context without hardcoding");
console.log("    3  Protocol Errors → Debugging resource and tool failures");
console.log("    4  Security Scope → The blast radius of exposing raw files");
console.log("    5  The Ecosystem Payoff → LLM uses Prompts, Resources, and Tools");
console.log(BORDER);
