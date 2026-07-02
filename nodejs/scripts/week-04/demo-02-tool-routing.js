/**
 * Demo 2: Tool Routing — Multiple tools, model chooses
 *
 * Run: node scripts/week-04/demo-02-tool-routing.js
 */
import { runToolLoopWithTrace } from "../../src/tools.js";

function printHeader(text) {
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
  console.log(`  \x1b[1m\x1b[35m${text}\x1b[0m`);
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
}

printHeader("Demo 2: Dynamic Tool Routing — LLM Selects & Parameterizes");
console.log();
console.log("  This demo showcases the LLM's ability to select the appropriate tool");
console.log("  from a list of multiple available options and extract target parameters.");
console.log();

const queries = [
  "Is the auth-service healthy?",
  "What were the last 3 deployments for payment-api?",
  "Are there any active incidents for inventory-service?",
];

for (let i = 0; i < queries.length; i++) {
  const q = queries[i];
  console.log(`  \x1b[1mQuery #${i + 1}:\x1b[0m "${q}"`);
  console.log("  Routing query...");
  const trace = await runToolLoopWithTrace(q);

  if (trace.tool_calls && trace.tool_calls.length > 0) {
    for (const tc of trace.tool_calls) {
      console.log(`    🟢 \x1b[32mRouted to Tool:\x1b[0m \x1b[1m${tc.name}\x1b[0m`);
      console.log(`    📥 \x1b[34mExtracted Args:\x1b[0m ${JSON.stringify(tc.args)}`);
    }
  } else {
    console.log("    ⚪ \x1b[33mNo tools required.\x1b[0m Answered directly using training weights.");
  }
  console.log(`    🤖 \x1b[36mFinal Answer:\x1b[0m ${trace.answer}`);
  console.log();
  console.log(`  ${"─".repeat(76)}`);
  console.log();
}

console.log("\x1b[1m\x1b[36mHow it works:\x1b[0m");
console.log("  By binding tool definitions (name, description, Zod schema schema) to the");
console.log("  LLM call, the model matches user intent against descriptions and outputs");
console.log("  exactly the parameters needed to fetch the live data.");
console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
