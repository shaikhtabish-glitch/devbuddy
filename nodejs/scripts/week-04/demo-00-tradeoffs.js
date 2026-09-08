/**
 * Demo 0: Tool Use — the tradeoffs and when NOT to use it (Node.js)
 *
 * THE MESSAGE OF THE WEEK: Week 3 gave the model a memory — you boxed its
 * input (retrieval). Week 4 gives it hands — you box its actions (tools).
 * The model proposes. Your code disposes.
 *
 * Print-only (no LLM, no network). Run: node scripts/week-04/demo-00-tradeoffs.js
 */
const BORDER = "=".repeat(70);

console.log(BORDER);
console.log("  Demo 0: Tool Use — Tradeoffs & When NOT to Use It");
console.log(BORDER);
console.log();

console.log("  THE BOUNDARY");
console.log("  ~~~~~~~~~~~~");
console.log("  The model never runs your code. It returns a REQUEST ({name, args});");
console.log("  your application decides whether that request becomes an action.");
console.log("  Safety never comes from the model — it comes from the boundary");
console.log("  you draw: whitelist, validation, retry, denial, audit log.");
console.log();

console.log("  The loop");
console.log("  ~~~~~~~~");
console.log("  Request → Decide (model) → Execute (your code) → Return → Answer");
console.log("  Every round-trip = another LLM call = latency + tokens.");
console.log();

console.log("  PROS — why you wire tools");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  • LIVE data. The model answers from your systems, not stale training.");
console.log("  • GROUNDED decisions. The answer rests on an executed, checkable result.");
console.log("  • EXTENSIBLE. Add a capability = add a tool; no prompt surgery.");
console.log("  • AUDITABLE. Every action is a recorded decision you can replay.");
console.log();

console.log("  CONS — what you are really paying");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  • LATENCY. Each tool round adds a full LLM call (seconds, not ms).");
console.log("  • COST. Tool results re-enter the context; tokens compound per round.");
console.log("  • A NEW FAILURE SURFACE. Tools crash, time out, return bad data.");
console.log("  • MISROUTING. The model can pick the wrong tool or skip a needed one.");
console.log("  • INJECTION SURFACE. A prompt can be tricked into calling a tool with");
console.log("    hostile args — your whitelist + validation are the only defence.");
console.log();

console.log("  WHEN NOT TO USE TOOL CALLING");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  • DETERMINISTIC pipeline (A then B then C every time) → just write code.");
console.log("  • ONE tool, always the same call → call the function directly.");
console.log("  • The answer must be <100 ms with zero failure modes → no LLM in the");
console.log("    critical path.");
console.log();

console.log("  WHERE THE CONTROL LIVES (say this out loud)");
console.log("  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
console.log("  Which tool / what args  → model decides; MY descriptions trained it.");
console.log("  Whether it actually runs → MY whitelist, not the model.");
console.log("  Retry / denial / fallback→ CODE decisions: deterministic, testable.");
console.log("  What it cost / did       → MY trace and a bounded loop.");
console.log("  When not to give it hands→ deterministic paths are just code.");
console.log();

console.log(BORDER);
console.log("  Demos 1–5 then show each of these in action:");
console.log("    1  wire one tool          → the boundary");
console.log("    2  route between tools    → descriptions are the design lever");
console.log("    3  make a tool fail       → retry & denial live in YOUR code");
console.log("    4  trace the full loop    → audit log + the bill");
console.log("    5  RAG as a tool          → a tool is just data with a name");
console.log(BORDER);
