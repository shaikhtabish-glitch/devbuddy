/**
 * Demo 2: Tool Routing — Two tools, model picks the right one (Node.js)
 *
 * THE POINT OF THIS DEMO: two tools, one question. The model picks — but it
 * is YOUR descriptions that taught it to pick. Routing is a design problem,
 * not a model problem. Vague description → vague routing.
 *
 *   Part A — Observed routing: real tools from src/tools.js, several
 *            questions, print what the model ACTUALLY called.
 *   Part B — The lever: same question against VAGUE vs PRECISE descriptions.
 *
 * Run: node scripts/week-04/demo-02-tool-routing.js
 */
import readline from "readline/promises";
import { stdin as input, stdout as output } from "process";
import { z } from "zod";
import { tool } from "@langchain/core/tools";
import { HumanMessage } from "@langchain/core/messages";
import { ALL_TOOLS, buildStatus, recentDeploys } from "../../src/tools.js";
import { getLlm } from "../../src/llm.js";

const BORDER = "=".repeat(70);

async function pause(msg = "  ⏸  Press Enter to continue… ") {
  if (!process.stdin.isTTY) return;
  const rl = readline.createInterface({ input, output });
  await rl.question(msg);
  rl.close();
}

async function decideCalls(question, tools) {
  const llm = getLlm({ temperature: 0.0 });
  const response = await llm.bindTools(tools).invoke([new HumanMessage(question)]);
  return response.tool_calls || [];
}

function printCalls(calls) {
  if (!calls.length) {
    console.log("       → NO tool called — the model answered directly.");
    return;
  }
  for (const tc of calls) {
    console.log(`       → ${tc.name}(${JSON.stringify(tc.args)})`);
  }
}

// ── Part B tool variants: same tools, two levels of description ──
const SERVICE = z.object({ service_name: z.string().describe("Service name") });
const SERVICE_LIMIT = z.object({
  service_name: z.string().describe("Service name"),
  limit: z.number().optional().nullable().default(5).describe("Max deploys"),
});

const vagueStatus = tool(async ({ service_name }) => buildStatus(service_name), {
  name: "get_build_status",
  description: "Get service information.",
  schema: SERVICE,
});

const vagueDeploys = tool(async ({ service_name, limit = 5 }) => recentDeploys(service_name, limit), {
  name: "get_recent_deploys",
  description: "Get records.",
  schema: SERVICE_LIMIT,
});

const preciseStatus = tool(async ({ service_name }) => buildStatus(service_name), {
  name: "get_build_status",
  description:
    "Return the current build/health status for a service: 'healthy', 'degraded', " +
    "'down', or 'unknown', plus last deploy time. Use for questions like 'is X healthy?'",
  schema: SERVICE,
});

const preciseDeploys = tool(async ({ service_name, limit = 5 }) => recentDeploys(service_name, limit), {
  name: "get_recent_deploys",
  description:
    "Return the last N deployments for a service (sha, author, timestamp, status). " +
    "Use for questions like 'what was deployed recently for X?' or 'is X healthy?'",
  schema: SERVICE_LIMIT,
});

const VAGUE = [vagueStatus, vagueDeploys];
const PRECISE = [preciseStatus, preciseDeploys];

console.log(BORDER);
console.log("  Demo 2: Tool Routing — Observed, then the Description Lever");
console.log(BORDER);
console.log();

// ── Part A ─────────────────────────────────────────────────────
console.log("  ── Part A: Observed routing (real tools from src/tools.js) ──");
console.log();
console.log("  Four questions, one LLM call each. Read what the model ACTUALLY");
console.log("  calls — outcomes vary run to run, so classify, don't assume.");
console.log();
console.log("  ⏸  PAUSE & PREDICT: for each question below, which tool should");
console.log("     it call? Write your guess, then continue.");
await pause();
console.log();

const questions = [
  "Is the auth-service healthy?",
  "What were the last 2 deployments for payment-api?",
  "Are there any active incidents for inventory-service?",
  "What's the latest build status?", // deliberately ambiguous — no service
];

for (const q of questions) {
  console.log(`  User: ${q}`);
  printCalls(await decideCalls(q, ALL_TOOLS));
  console.log();
}
console.log("  Note Q4: 'the latest build status' names no service. Watch whether");
console.log("  the model guesses one, asks, or skips the tool.");
console.log();

// ── Part B ─────────────────────────────────────────────────────
console.log("  ── Part B: The description lever ───────────────────────────");
console.log();
console.log("  Same question, same two tools, same raw data. ONLY the tool");
console.log("  descriptions change. Routing is a design problem.");
console.log();
const questionB = "Is the payment-api healthy and what was deployed most recently?";

console.log("  ⏸  PAUSE & PREDICT: the vague set says 'Get service information.' /");
console.log("     'Get records.' Will it route the same as the precise set?");
await pause();
console.log();

console.log(`  Question: ${questionB}`);
console.log();
console.log("  VAGUE descriptions:");
printCalls(await decideCalls(questionB, VAGUE));
console.log();
console.log("  PRECISE descriptions:");
printCalls(await decideCalls(questionB, PRECISE));
console.log();

console.log(BORDER);
console.log("  ROUTING IS A DESIGN PROBLEM, NOT A MODEL PROBLEM.");
console.log("  Above are the OBSERVED calls for each case — they vary run to");
console.log("  run. The lever you control is not the model; it is each tool's");
console.log("  name and description. Vague description → vague routing.");
console.log();
console.log("  YOUR TURN:");
console.log("    • Add a THIRD tool whose purpose overlaps tool #2 — does routing");
console.log("      degrade? When is 'fewer, sharper tools' better than more?");
console.log("    • Run the same question 5×. How stable is routing at temp 0?");
console.log(BORDER);
