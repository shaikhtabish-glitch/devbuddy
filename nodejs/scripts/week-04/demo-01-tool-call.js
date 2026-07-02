/**
 * Demo 1: Tool Call — Wire a tool, trace the loop
 *
 * Run: node scripts/week-04/demo-01-tool-call.js
 */
import { runToolLoop, runToolLoopWithTrace } from "../../src/tools.js";

// Helper for clean box drawing
function printHeader(text) {
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
  console.log(`  \x1b[1m\x1b[35m${text}\x1b[0m`);
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
}

printHeader("Demo 1: Tool Call — The Agent Loop (Request → Decide → Execute → Answer)");
console.log();
console.log("  This demo illustrates the boundaries of Function Calling:");
console.log("  1. The LLM receives a query and decides to call a tool.");
console.log("  2. The LLM halts execution and returns a structured tool call request.");
console.log("  3. Your local application code executes the tool locally.");
console.log("  4. The result is passed back to the LLM to generate the final answer.");
console.log();

const query = "Is the auth-service healthy?";
console.log(`  \x1b[1m\x1b[33m[1/3] Initiating Plain Query:\x1b[0m "${query}"`);
console.log("  Sending to LLM...");
const answer = await runToolLoop(query);
console.log(`  \x1b[1m\x1b[32m✔ Final Answer:\x1b[0m ${answer}`);
console.log();
console.log("  " + "─".repeat(76));
console.log();

console.log(`  \x1b[1m\x1b[33m[2/3] Tracing the Execution Loop:\x1b[0m`);
const trace = await runToolLoopWithTrace(query);

for (let i = 0; i < trace.steps.length; i++) {
  const step = trace.steps[i];
  console.log(`    \x1b[1mStep ${i + 1}: [${step.type.toUpperCase()}]\x1b[0m`);
  if (step.type === "decide") {
    console.log("    🤖 \x1b[36mLLM Decision:\x1b[0m Model inspected the query and detected tool parameters.");
    if (trace.tool_calls) {
      for (const tc of trace.tool_calls) {
        console.log(`       ↳ Target Tool: \x1b[1m${tc.name}\x1b[0m`);
        console.log(`       ↳ Arguments:   ${JSON.stringify(tc.args)}`);
      }
    }
  } else if (step.type === "execute") {
    console.log("    💻 \x1b[32mLocal Execution:\x1b[0m Application layer executed the tool locally.");
    console.log(`       ↳ Tool:   \x1b[1m${step.tool}\x1b[0m`);
    console.log(`       ↳ Output: \x1b[34m${step.result}\x1b[0m`);
  } else if (step.type === "answer") {
    console.log("    🤖 \x1b[36mLLM Synthesis:\x1b[0m Model read the tool output and formulated the final response.");
    console.log(`       ↳ Response: \x1b[32m"${step.content}"\x1b[0m`);
  }
  console.log();
}

console.log("  " + "─".repeat(76));
console.log();
console.log(`  \x1b[1m\x1b[33m[3/3] Key Takeaway:\x1b[0m`);
console.log("  \x1b[31m⚠️  CRITICAL BOUNDARY:\x1b[0m The LLM did not run the health check code itself.");
console.log("  It only generated the JSON schema instructing *us* to run it. Your application");
console.log("  remains in absolute control of what gets executed and how sandbox keys are handled.");
console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
