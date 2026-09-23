/**
 * Demo 3: Tool Failure — Retry in the app layer, not the prompt
 *
 * THE POINT OF THIS DEMO: tools fail and models misbehave. Retry, denial,
 * and fallback are CODE decisions — deterministic, testable, auditable.
 * The prompt is the wrong place for safety. The model only ever sees the
 * final result: success or a structured error.
 *
 *   Act 1 — Retry in the app layer: normal → transient (retry) → exhausted.
 *   Act 2 — The guardrail: hostile/unknown tool calls are DENIED by code.
 *   Act 3 — The model sees the error: feed it the structured error and watch
 *           it degrade gracefully.
 *
 * Run: node scripts/week-04/demo-03-tool-failure.js
 */
import { z } from "zod";
import { tool } from "@langchain/core/tools";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { buildStatus, flaky, executeToolSafely } from "../../src/tools.js";
import { getLlm } from "../../src/llm.js";
import { BORDER, pause } from "./_common.js";

/**
 * A registry that maps get_build_status → a flaky wrapper of buildStatus.
 * The wrapper is built from the RAW function in src/tools (flaky()), so the
 * data stays in one place — only the failure behaviour is injected.
 */
function flakyStatusRegistry(failFirstN) {
  const impl = flaky(buildStatus, failFirstN);
  const flakyStatus = tool(
    async ({ service_name }) => impl(service_name),
    {
      name: "get_build_status",
      description: "Return the current build/health status of a service.",
      schema: z.object({ service_name: z.string() }),
    }
  );
  return { get_build_status: flakyStatus };
}

console.log(BORDER);
console.log("  Demo 3: Tool Failure — Retry & Denial Live in the App Layer");
console.log(BORDER);
console.log();
console.log("  The model proposes a call. YOUR code decides whether it runs,");
console.log("  whether it retries, and what the model sees. Nothing here lives");
console.log("  in the prompt.");
console.log();

// ═══════════════════════════════════════════════════════════════
// Act 1 — Retry in the app layer (deterministic, no LLM in the loop)
// ═══════════════════════════════════════════════════════════════
console.log("  ── Act 1: Retry in the app layer ────────────────────────────");
console.log();
console.log("  The same call, three times — only the failure behaviour changes:");
console.log("  flaky(buildStatus, failFirstN=N) wraps the RAW function.");
console.log();
const toolCall = { name: "get_build_status", args: { service_name: "payment-api" } };

const scenarios = [
  [0, "normal", "tool never fails"],
  [1, "transient", "fails once, then recovers"],
  [99, "exhausted", "always fails — retries burn out"],
];

for (const [failFirstN, label, meaning] of scenarios) {
  console.log(`  ── scenario: ${label.padEnd(10)} (${meaning}) ──`);
  const result = await executeToolSafely(toolCall, 2, {
    toolsByName: flakyStatusRegistry(failFirstN),
    verbose: true,
  });
  const parsed = JSON.parse(result);
  if (parsed.error) {
    console.log(`     ❌ structured error after ${parsed.attempts} attempts:`);
    console.log(`        ${parsed.error}`);
  } else {
    console.log(`     ✅ returned: ${result.slice(0, 110)}`);
  }
  console.log();
}

console.log("  Retries ran inside executeToolSafely() — your code, not the");
console.log("  model's. The model never saw the failure; it only ever sees the");
console.log("  final result: success, or a structured error.");
console.log();

// ═══════════════════════════════════════════════════════════════
// Act 2 — The guardrail: never trust the raw tool request
// ═══════════════════════════════════════════════════════════════
console.log("  ── Act 2: The guardrail — never trust the raw request ───────");
console.log();
console.log("  The model returns {name, args}. That is a REQUEST, not a fact.");
console.log("  Your registry decides if it deserves to become an action.");
console.log();
console.log("  ⏸  PAUSE & PREDICT: the model asks for 'delete_production_db'.");
console.log("     What should happen? Predict, then continue.");
await pause();
console.log();

const hostile = await executeToolSafely({ name: "delete_production_db", args: {} });
console.log(`  Request: delete_production_db({})`);
console.log(`  Response: ${hostile}`);
console.log("  → DENIED by the registry. The model can never reach code it was");
console.log("    not given — that is what the whitelist is for.");
console.log();

const unknownService = await executeToolSafely({
  name: "get_build_status",
  args: { service_name: "ghost-service" },
});
console.log(`  Request: get_build_status(ghost-service)`);
console.log(`  Response: ${unknownService}`);
console.log("  → A valid tool with bad args returns a structured 'no data' result.");
console.log("    No crash, no exception — the model can reason about it.");
console.log();

// ═══════════════════════════════════════════════════════════════
// Act 3 — The model sees the error (one LLM call)
// ═══════════════════════════════════════════════════════════════
console.log("  ── Act 3: The model sees the error ──────────────────────────");
console.log();
console.log("  Now the app-layer error is fed to the model. The model's job is");
console.log("  to degrade gracefully — tell the user what happened, not to");
console.log("  magically 'fix' the tool.");
console.log();
const exhausted = await executeToolSafely(
  { name: "get_build_status", args: { service_name: "payment-api" } },
  2,
  { toolsByName: flakyStatusRegistry(99) }
);
const llm = getLlm({ temperature: 0.0 });
const answer = await llm.invoke([
  new SystemMessage(
    "You are an engineering assistant. A monitoring tool was called but " +
      "returned a structured error. Report to the user what happened and " +
      "what the next step should be. Do not invent data."
  ),
  new HumanMessage(
    `Question: Is the payment-api healthy?\n\nTool result:\n${exhausted}`
  ),
]);
console.log("  Structured error given to model:");
console.log(`     ${exhausted}`);
console.log(`  Model's answer: ${String(answer.content).trim()}`);
console.log();

console.log(BORDER);
console.log("  THE MESSAGE: retry logic, denial, and error format are CODE");
console.log("  decisions — deterministic, testable, auditable. The model's");
console.log("  recovery is unreliable by design; your application layer is what");
console.log("  ships. Never trust the raw tool request; always route execution");
console.log("  through your own guardrail.");
console.log();
console.log("  YOUR TURN:");
console.log("    • Change maxRetries in Act 1 and watch the attempts count move.");
console.log("    • Add a retry-with-backoff for the exhausted case — should the");
console.log("      app retry 3 times, or fail fast and escalate? Why?");
console.log(BORDER);
