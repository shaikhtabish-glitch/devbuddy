/**
 * Demo 1: Tool Call — Wire a tool, watch the model call it (Node.js)
 *
 * THE POINT OF THIS DEMO is not that the model called a function — it is
 * that the model could NOT have run it. It returned a request
 * ({name, args}); your code did the work. The model proposes.
 * Your code disposes.
 *
 * Run: node scripts/week-04/demo-01-tool-call.js
 */
import readline from "readline/promises";
import { stdin as input, stdout as output } from "process";
import { HumanMessage, ToolMessage } from "@langchain/core/messages";
import { executeToolSafely, getBuildStatus } from "../../src/tools.js";
import { getLlm } from "../../src/llm.js";

const BORDER = "=".repeat(70);

async function pause(msg = "  ⏸  Press Enter to continue… ") {
  if (!process.stdin.isTTY) return;
  const rl = readline.createInterface({ input, output });
  await rl.question(msg);
  rl.close();
}

console.log(BORDER);
console.log("  Demo 1: Wire a Tool → Watch the Model Call It");
console.log(BORDER);
console.log();

console.log("  ── Step 1: Bind the tool ───────────────────────────────────");
console.log();
console.log("  The model sees get_build_status as a schema — a description of a");
console.log("  function it MAY ask for. It never sees the implementation.");
console.log();
const llm = getLlm({ temperature: 0.0 });
const llmWithTools = llm.bindTools([getBuildStatus]);

const question = "Is the payment-api healthy?";
console.log("  ── Step 2: Ask ─────────────────────────────────────────────");
console.log(`  User: ${question}`);
console.log();
console.log("  ⏸  PAUSE & PREDICT: will it answer from training data, or call");
console.log("     the tool for live data?");
await pause();
console.log();

const response = await llmWithTools.invoke([new HumanMessage(question)]);

if (!response.tool_calls || response.tool_calls.length === 0) {
  console.log("  Model answered directly — no tool call this time:");
  console.log(`  ${response.content}`);
  console.log();
  console.log("  That is a routing decision too: the model judged it did not need");
  console.log("  live data. Ask again with a service name and watch it flip.");
} else {
  const tc = response.tool_calls[0];
  console.log("  ── Step 3: See the request ───────────────────────────────");
  console.log(`  Model decided to call: ${tc.name}`);
  console.log(`  With arguments:         ${JSON.stringify(tc.args)}`);
  console.log("  That is ALL the model produced — a request, not an action.");
  console.log();

  console.log("  ── Step 4: Your code executes it ─────────────────────────");
  console.log("  The request goes through executeToolSafely() — the app layer,");
  console.log("  not the model, decides whether it runs.");
  console.log();
  const result = await executeToolSafely(tc);
  console.log(`  Tool returned: ${result}`);
  console.log();

  console.log("  ── Step 5: Inject result → final answer ──────────────────");
  const messages = [
    new HumanMessage(question),
    response,
    new ToolMessage({ content: result, tool_call_id: tc.id }),
  ];
  const final = await llmWithTools.invoke(messages);
  console.log(`  Model: ${final.content}`);
  console.log();
}

console.log(BORDER);
console.log("  The loop: Request → Decide → Execute → Return → Answer");
console.log("  THE BOUNDARY: the model could NOT have run get_build_status.");
console.log("  It returned a request. Your code executed it. You decide whether");
console.log("  a request becomes an action — and you keep the trace.");
console.log("  The model proposes. Your code disposes.");
console.log(BORDER);
