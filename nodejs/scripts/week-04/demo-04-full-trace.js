/**
 * Demo 4: Full Trace — Every step of the tool loop, visible
 *
 * Run: node scripts/week-04/demo-04-full-trace.js
 */
import { runToolLoopWithTrace } from "../../src/tools.js";

function printHeader(text) {
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
  console.log(`  \x1b[1m\x1b[35m${text}\x1b[0m`);
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
}

printHeader("Demo 4: Full Multi-Step Execution Trace Visualizer");
console.log();
console.log("  When a query requires multiple tools, the agent loops sequentially.");
console.log("  This trace visualizes every message and payload exchanged between the");
console.log("  LLM and the application execution context.");
console.log();

const query = "Check payment-api health, recent deploys, and active incidents.";
console.log(`  \x1b[1mStarting Complex Query:\x1b[0m "${query}"`);
console.log("  Tracing execution loop...");
console.log();

const trace = await runToolLoopWithTrace(query);

for (let i = 0; i < trace.steps.length; i++) {
  const step = trace.steps[i];
  console.log(`  \x1b[1m[Step ${i + 1}] Transition: ${step.type.toUpperCase()}\x1b[0m`);
  
  if (step.type === "decide") {
    console.log("  🤖 \x1b[36mModel Decision:\x1b[0m Inspected current conversation state and decided tools were needed.");
    if (trace.tool_calls) {
      console.log("     Tool calls planned:");
      for (const tc of trace.tool_calls) {
        console.log(`     👉 \x1b[32m${tc.name}\x1b[0m with args ${JSON.stringify(tc.args)}`);
      }
    }
  } else if (step.type === "execute") {
    console.log(`  💻 \x1b[32mApp Execution of ${step.tool}:\x1b[0m`);
    console.log("     ┌────────────────────────────────────────────────────────────────────────┐");
    let payload = step.result;
    try {
      payload = JSON.stringify(JSON.parse(step.result), null, 2);
    } catch (e) {
      // Handle truncated JSON or plain strings
    }
    for (const line of payload.split("\n")) {
      const cleanLine = line.substring(0, 70);
      console.log(`     │ ${cleanLine.padEnd(70)} │`);
    }
    console.log("     └────────────────────────────────────────────────────────────────────────┘");
  } else if (step.type === "answer") {
    console.log("  🤖 \x1b[36mFinal Response Generation:\x1b[0m Synthesized all previous inputs into readable prose.");
    console.log(`     \x1b[1m\x1b[32mResult:\x1b[0m "${step.content}"`);
  }
  console.log();
}

console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
