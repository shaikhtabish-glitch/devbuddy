/**
 * Demo 2: Tool Routing — Multiple tools, model chooses
 *
 * Run: node scripts/week-04/demo-02-tool-routing.js
 */
import { runToolLoopWithTrace } from "../../src/tools.js";

console.log("=".repeat(60));
console.log("  Demo 2: Tool Routing — Model picks the right tool");
console.log("=".repeat(60));
console.log();

const queries = [
  "Is the auth-service healthy?",
  "What were the last 3 deployments for payment-api?",
  "Are there any active incidents for inventory-service?",
];

for (const q of queries) {
  console.log(`  Query: "${q}"`);
  const trace = await runToolLoopWithTrace(q);
  if (trace.tool_calls) {
    console.log(`    Tools called: ${trace.tool_calls.map((t) => t.name).join(", ")}`);
  }
  console.log(`    Answer: ${trace.answer.slice(0, 100)}`);
  console.log();
}

console.log("  The model routed each question to the right tool.");
console.log("=".repeat(60));
