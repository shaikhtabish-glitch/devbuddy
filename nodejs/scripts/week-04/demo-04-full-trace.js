/**
 * Demo 4: Full Trace — Every step of the tool loop, visible
 *
 * Run: node scripts/week-04/demo-04-full-trace.js
 */
import { runToolLoopWithTrace } from "../../src/tools.js";

console.log("=".repeat(60));
console.log("  Demo 4: Full Trace — Every step visible");
console.log("=".repeat(60));
console.log();

const trace = await runToolLoopWithTrace(
  "Check payment-api health, recent deploys, and active incidents."
);

console.log("  Query:", trace.query);
console.log();
for (let i = 0; i < trace.steps.length; i++) {
  const step = trace.steps[i];
  console.log(`  Step ${i + 1} [${step.type}]:`);
  if (step.tool) console.log(`    Tool: ${step.tool}`);
  const content = step.content || step.result || "";
  console.log(`    ${content}`);
  console.log();
}
console.log("  Final Answer:", trace.answer);
console.log();
console.log("  This is the full tool-calling loop — every decision visible.");
console.log("=".repeat(60));
