/**
 * Demo 3: Tool Failure — Tool throws, app layer handles it
 *
 * Run: node scripts/week-04/demo-03-tool-failure.js
 */
import { runToolLoop, executeToolSafely } from "../../src/tools.js";

function printHeader(text) {
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
  console.log(`  \x1b[1m\x1b[35m${text}\x1b[0m`);
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
}

printHeader("Demo 3: Graceful Tool Failure & Application Guardrails");
console.log();
console.log("  What happens when the tool fails, is passed bad arguments, or is unknown?");
console.log("  Your application layer must handle errors safely and feed constructive feedback");
console.log("  back to the LLM so it can report issues without crashing.");
console.log();

// Scenario 1: Non-existent service name passed to a valid tool
const query1 = "Is the nonexistent-service healthy?";
console.log(`  \x1b[1mScenario 1: Bad arguments passed to valid tool\x1b[0m`);
console.log(`  Query: "${query1}"`);
console.log("  Running...");
const answer1 = await runToolLoop(query1);
console.log(`  🤖 \x1b[36mLLM Response:\x1b[0m ${answer1}`);
console.log("  → The tool returned a structured error JSON, allowing the LLM to explain");
console.log("    the status cleanly instead of crashing the process.");
console.log();
console.log(`  ${"─".repeat(76)}`);
console.log();

// Scenario 2: Model attempts to call an unauthorized/nonexistent tool
console.log(`  \x1b[1mScenario 2: Guarding against unauthorized tool execution\x1b[0m`);
console.log("  Attempting to execute direct instruction: { name: 'delete_production_db', args: {} }");
console.log("  Executing safely...");
const result = await executeToolSafely({
  name: "delete_production_db",
  args: {},
});
console.log(`  💻 \x1b[31mExecution Layer Result:\x1b[0m ${result}`);
console.log();
console.log("  → Guardrail: Our local execution router (executeToolSafely) checked its registry,");
console.log("    rejected the call, and returned a list of safe available tools.");
console.log();
console.log(`  ${"─".repeat(76)}`);
console.log();
console.log("  \x1b[1m\x1b[33mKey Takeaway:\x1b[0m");
console.log("  Never trust the LLM's raw tool request. Always route execution through a registry");
console.log("  guardrail (`executeToolSafely`) that enforces schema limits and traps exceptions.");
console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
