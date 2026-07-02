/**
 * Demo 1: Tool Call — Wire a tool, trace the loop
 *
 * Run: node scripts/week-04/demo-01-tool-call.js
 */
import { runToolLoop, runToolLoopWithTrace } from "../../src/tools.js";

console.log("=".repeat(60));
console.log("  Demo 1: Tool Call — Request → Decide → Execute → Answer");
console.log("=".repeat(60));
console.log();

// Simple call
console.log("  Query: 'Is the auth-service healthy?'");
const answer = await runToolLoop("Is the auth-service healthy?");
console.log(`  Answer: ${answer}`);
console.log();

// Traced call
console.log("  Same query, with full trace:");
const trace = await runToolLoopWithTrace("Is the auth-service healthy?");
for (const step of trace.steps) {
  console.log(`    [${step.type}] ${step.content || step.result || ""}`);
}
console.log();
console.log("  The model never executed code. It decided. Your code executed.");
console.log("=".repeat(60));
