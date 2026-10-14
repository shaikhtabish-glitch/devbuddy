/**
 * Demo 2: Dynamic Routing — the model PROPOSES, the registry disposes
 *
 * Runs the dynamic agent on 3 queries and prints, for every planning
 * decision: what the model proposed, what the code accepted/rejected, and
 * why. That proposal→decision stream — not the step list — is the lesson.
 *
 * Also measures fixed vs dynamic on the same query (steps + cost).
 *
 * Requires: MCP server (:3001) + Qdrant (:6333)
 * Run: node scripts/week-06/demo-02-dynamic-routing.js
 */
import {
  runDynamicAgent,
  runFixedChain,
  formatReport,
} from "../../src/agent.js";

function showPlans(result) {
  const plans = result.messages.filter((m) => m.step === "plan");
  if (!plans.length) return;
  console.log("      🧠  plan decisions (LLM proposes → code disposes):");
  for (const p of plans) {
    const proposal = p.proposal ?? "—";
    const decision = p.decision ?? "?";
    const cost = p.cost ? `  · $${p.cost.toFixed(6)}` : "";
    const marker = decision === "accept" ? "✅" : "⚠️ ";
    const reason = p.reason ? `  (${p.reason})` : "";
    const dispatched =
      p.corrected_to && p.corrected_to !== proposal
        ? `  → dispatched: ${p.corrected_to}`
        : "";
    console.log(
      `         ${marker} proposed ${proposal} → ${decision}${reason}${dispatched}${cost}`
    );
  }
}

console.log();
console.log("=".repeat(65));
console.log("  Demo 2: Dynamic Routing — LLM proposes, registry disposes");
console.log("=".repeat(65));
console.log();
console.log("  The graph's ROUTES are still static; which route is taken at");
console.log("  runtime comes from a planning node. The model may only propose");
console.log("  steps the registry allows for this query's category — watch the");
console.log("  decisions below: accepted, corrected, or handed to the guard.");
console.log();

const queries = [
  ["Is payment-api healthy?", "health only"],
  [
    "What was deployed recently for payment-api and are there any incidents?",
    "multi-intent (deploys + incidents)",
  ],
  ["Give me a full readiness assessment for payment-api.", "full assessment"],
];

for (let i = 0; i < queries.length; i++) {
  const [query, label] = queries[i];
  console.log(`  ── ${label} ──`);
  console.log(`  📥  QUERY: "${query}"`);
  const result = await runDynamicAgent(query);
  await new Promise((r) => setTimeout(r, 1000)); // let SSE settle

  // The path is what the agent RECORDED — an audit trail, not a guess.
  const path = result.messages.map((m) => m.step);

  console.log(
    `  ⚡  Steps: ${result.steps}  |  Cost: $${result.cost.toFixed(6)}`
  );
  console.log(`  🔀  Path:   ${path.join(" → ")}`);
  showPlans(result);
  if (result.error) console.log(`  ⚠️   Error:  ${result.error}`);
  console.log(`  ${"─".repeat(59)}`);
  console.log(formatReport(result.report));
  console.log();

  // ── Measured comparison: same query through the fixed chain ──
  if (i === 0) {
    console.log("  📊  SAME query through demo-01's fixed chain:");
    const fixed = await runFixedChain(query);
    await new Promise((r) => setTimeout(r, 1000));
    console.log(
      `      fixed   : ${fixed.steps} steps · $${fixed.cost.toFixed(6)}`
    );
    console.log(
      `      dynamic : ${result.steps} steps · $${result.cost.toFixed(6)}`
    );
    console.log(
      `      → dynamic pays for planning LLM calls; fixed pays for`
    );
    console.log(`        running its steps whether you needed them or not.`);
    console.log();
  }
}

console.log("=".repeat(65));
console.log("  What varied between the three queries? Not the graph — the");
console.log("  PLAN decisions. Same nodes, same edges, different runtime path,");
console.log("  different cost. Measure your own: take-home Part A runs 5");
console.log("  queries through both and compares.");
console.log("=".repeat(65));
console.log();
process.exit(0);