/**
 * Demo 5 (C3): Guards — the agent knows when to stop
 *
 * Test 1: guarded chain WITH check_build → validity guard PASSES → report
 * Test 2: same query, check_build removed → guard BLOCKS (typed answer,
 *         zero LLM spend on a report — proven by the cost line)
 * Test 3: refusal — "Deploy ..." → registry-driven refusal
 * Test 4: budget guard — maxSteps forced to 2 → run stops with a typed
 *         answer instead of running away
 *
 * Requires: MCP server (:3001) + Qdrant (:6333)
 * Test 3 needs only the LLM.
 * Run: node scripts/week-06/demo-05-guard-and-refusal.js
 */
import {
  runGuardedChain,
  runDynamicAgent,
  formatReport,
  BUDGET,
} from "../../src/agent.js";

const HEALTHY_QUERY = "Is auth-service healthy?";

function show(result) {
  console.log(`  🔀  Path: ${result.messages.map((m) => m.step).join(" → ")}`);
  console.log(`  [state] build_status = ${JSON.stringify(result.build_status)}`);
  // The guard's DECISION is in the audit — print it, don't infer it.
  for (const m of result.messages) {
    if (m.step === "validate") {
      console.log(
        m.status === "passed"
          ? "  🛡  PASS → model may generate the report"
          : `  🛑 BLOCKED (${m.category})`
      );
    }
  }
  if (result.error) console.log(`  🛑  ${result.error}`);
  console.log(`  ${"─".repeat(59)}`);
  console.log(formatReport(result.report));
  console.log(`  💰  cost so far: $${result.cost.toFixed(6)}`);
  console.log();
  return result;
}

console.log();
console.log("=".repeat(65));
console.log("  Demo 5 (C3): Validity Guard + Refusal + Budget");
console.log("=".repeat(65));
console.log();
console.log("  Three guards, three jobs: validity (state must be acceptable),");
console.log("  structural (registry decides what's possible), budget (steps/cost");
console.log("  ceiling). All three produce TYPED answers — no LLM, no prose.");
console.log();

// ── Test 1: validity guard PASSES when required data present ──

console.log("  ── Test 1: build checked → guard PASSES → report generated ──");
// auth-service: latest deploy success, incident resolved — unambiguous
// ground truth, so this pass-path is stable across runs.
console.log(`  📥  QUERY: "${HEALTHY_QUERY}"`);
const r1 = show(await runGuardedChain(HEALTHY_QUERY));

// ── Test 2: validity guard STOPS when required data missing ───

console.log("  ── Test 2: check_build REMOVED → guard STOPS the agent ──");
console.log(`  📥  QUERY: "${HEALTHY_QUERY}"`);
const r2 = show(await runGuardedChain(HEALTHY_QUERY, false));

const path2 = r2.messages.map((m) => m.step);
console.log(
  `  💰  COST PROOF: test 1 = $${r1.cost.toFixed(6)}  |  ` +
    `test 2 = $${r2.cost.toFixed(6)}`
);
console.log(
  `      generate_report in test 2's path? ` +
    `${path2.includes("generate_report") ? "YES (unexpected!)" : "NO — the guard wrote"}`
);
console.log(`      the blocked answer in CODE. A guard that spends tokens`);
console.log(`      isn't a guard, it's a suggestion.`);
console.log();

// ── Test 3: refusal — no deploy tool exists ───────────────────

console.log("  ── Test 3: 'Deploy ...' → refused from the registry ──");
const DEPLOY_QUERY = "Deploy auth-service to production";
console.log(`  📥  QUERY: "${DEPLOY_QUERY}"`);
const r3 = show(await runDynamicAgent(DEPLOY_QUERY));
for (const m of r3.messages) {
  if (m.step === "plan") {
    console.log(
      `  🧠  plan: proposal=${JSON.stringify(m.proposal)} → ${m.decision}` +
        `  (${m.reason || "registry lookup"})`
    );
  }
}
console.log("  The refusal message lists ONLY registry entries — the model");
console.log("  never got to invent what the agent can do.");
console.log();

// ── Test 4: budget guard — stop a runaway run ─────────────────

console.log("  ── Test 4: budget guard — maxSteps forced to 2 ──");
const BUDGET_QUERY = "Give me a full readiness assessment for payment-api.";
console.log(`  📥  QUERY: "${BUDGET_QUERY}"`);
console.log(`  🔧  maxSteps: ${BUDGET.maxSteps} → 2 (temporarily)`);

const savedSteps = BUDGET.maxSteps;
BUDGET.maxSteps = 2;
let r4;
try {
  r4 = await runDynamicAgent(BUDGET_QUERY);
} finally {
  BUDGET.maxSteps = savedSteps;
}

console.log(`  🔀  Path: ${r4.messages.map((m) => m.step).join(" → ")}`);
console.log(
  `  ⚡  Steps: ${r4.steps} (limit was 2)  |  next_step=${JSON.stringify(r4.next_step)}`
);
console.log(`  ${"─".repeat(59)}`);
console.log(formatReport(r4.report));
console.log(
  `  💰  cost: $${r4.cost.toFixed(6)} — stopped BEFORE burning the budget;`
);
console.log(
  `      the blocked answer cost 0 tokens (typed, not generated).`
);
console.log();
console.log(`  🔧  maxSteps restored to ${BUDGET.maxSteps}.`);
console.log("=".repeat(65));
console.log();
process.exit(0);