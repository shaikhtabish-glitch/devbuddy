/**
 * Demo 3: Tool Failure — Tool throws, app layer handles it
 *
 * Run: node scripts/week-04/demo-03-tool-failure.js
 */
import { runToolLoop, executeToolSafely } from "../../src/tools.js";

console.log("=".repeat(60));
console.log("  Demo 3: Tool Failure — Application-layer error handling");
console.log("=".repeat(60));
console.log();

// 1. Unknown service — tool returns structured error
console.log("  Query: 'Is the nonexistent-service healthy?'");
const answer1 = await runToolLoop("Is the nonexistent-service healthy?");
console.log(`  Answer: ${answer1}`);
console.log("  → Tool returned 'unknown' with error. App handled it gracefully.");
console.log();

// 2. Unknown tool — executeToolSafely catches it
console.log("  Calling non-existent tool directly:");
const result = await executeToolSafely({
  name: "delete_production_db",
  args: {},
});
console.log(`  Result: ${result}`);
console.log();
console.log("  The model decides. Your code executes and enforces.");
console.log("=".repeat(60));
