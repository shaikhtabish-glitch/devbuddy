/**
 * Demo 4 (C2): Missing-Step Hallucination — remove a node, watch it invent
 *
 * The demo-01 chain with check_build REMOVED and NO guard. The naive report
 * node renders missing state as '{}' and gives the model no ground rules —
 * so when BUILD shows up empty, the model completes the report anyway.
 *
 * Why: the LLM predicts tokens, it doesn't reason about missing data.
 * This is the SAME mechanism as Week 4's tool-error hallucination.
 *
 * Requires: MCP server (:3001) + Qdrant (:6333)
 * Run: node scripts/week-06/demo-04-missing-step.js
 */
import {
  runMissingStepAgent,
  runGuardedChain,
  formatReport,
} from "../../src/agent.js";

const QUERY = "Is payment-api ready for release?";

console.log();
console.log("=".repeat(65));
console.log("  Demo 4 (C2): Missing-Step Hallucination");
console.log("=".repeat(65));
console.log();
console.log("  The check_build node has been REMOVED from the graph.");
console.log("  state['build_status'] will be '' — never checked, no guard.");
console.log("  Watch what the report does with an empty build status.");
console.log();

// ── Run the broken graph ───────────────────────────────────────

const result = await runMissingStepAgent(QUERY);

console.log(`  📥  QUERY: "${QUERY}"`);
console.log(`  🔀  Path:  ${result.messages.map((m) => m.step).join(" → ")}`);
console.log();
console.log(`  [state] build_status = ${JSON.stringify(result.build_status)}`);
console.log(
  `          → Was the build ever checked? ${
    result.build_status ? "yes" : "NO — the node does not exist"
  }`
);
console.log();

console.log(`  ${"─".repeat(59)}`);
console.log(`  📤  NAIVE REPORT (node rendered BUILD: {}):`);
console.log(formatReport(result.report));
console.log();

// ── Did it invent build data? ──────────────────────────────────
//
// Structural detection — check claims against STATE, not keywords:
//
// 1) fabricated tool evidence: an evidence chunk citing source='tool'
//    for build data while state['build_status'] is empty is a lie the
//    state itself proves.
// 2) affirmative build claims: status words near 'build' — with hedges
//    ("not checked", "no data", "unknown") excluded, because an honest
//    hedge is NOT a hallucination.
// (A naive keyword count would false-positive on "incidents" — it
//  contains "ci" — and would flag honest hedges that mention "build".)

const report = result.report;
const fabricated = (report.evidence || [])
  .filter((e) => e.source === "tool" && e.content.toLowerCase().includes("build"))
  .map((e) => e.content.slice(0, 80).replace(/\n/g, " "));

const haystack = [
  report.answer,
  ...(report.evidence || []).map((e) => e.content),
  ...(report.verdict?.blockers || []),
  ...(report.verdict?.recommended_next_steps || []),
]
  .join(" ")
  .toLowerCase();

const affirmative = haystack.match(
  /build[^.\n]{0,60}\b(healthy|passing|green|success\w*|degraded|down|failing|compiled)\b|\b(healthy|passing|green|compiled)\b[^.\n]{0,40}build/
);
const hedged = haystack.match(
  /build[^.\n]{0,60}(not checked|no (build )?data|never (been )?checked|unknown|missing)|(not checked|no data|never checked)[^.\n]{0,40}build/
);

const detected = fabricated.length > 0 || Boolean(affirmative);

console.log("  🔎  DETECTION (state vs. claims — not keyword counting):");
console.log(`      state['build_status']      : ${JSON.stringify(result.build_status)} (never checked)`);
console.log(`      fabricated tool evidence   : ${fabricated.length ? fabricated.join(" | ") : "none"}`);
console.log(
  `      affirmative build claim    : ${affirmative ? JSON.stringify(affirmative[0]) : "none"}`
);
if (hedged) console.log(`      hedge present              : ${JSON.stringify(hedged[0])}`);
console.log();
if (detected) {
  console.log("      → HALLUCINATION: the report asserts (or cites tool evidence for)");
  console.log("        build data that state says was never collected. The model");
  console.log("        filled a gap YOUR graph left open — it predicts tokens,");
  console.log("        it doesn't check state.");
} else {
  console.log("      → The model hedged this run (no affirmative claim). The");
  console.log("        VULNERABILITY is still real: nothing in this graph stops");
  console.log("        it from inventing. Hedging is luck, not a guardrail.");
}
console.log();

// ── The same missing step, with the guard attached ─────────────

console.log("=".repeat(65));
console.log("  SAME missing step — now with the C3 validity guard attached");
console.log("=".repeat(65));
console.log();

const guarded = await runGuardedChain(QUERY, false);

console.log(`  🔀  Path: ${guarded.messages.map((m) => m.step).join(" → ")}`);
console.log(`  [state] build_status = ${JSON.stringify(guarded.build_status)}`);
console.log(`  🛑  GUARD: ${guarded.error}`);
console.log();
console.log("  📤  TYPED BLOCKED ANSWER (written by the guard, no LLM):");
console.log(formatReport(guarded.report));
console.log();
console.log("  The agent REFUSED to produce a confident report from empty state.");
console.log("  Guard = difference between 'tried its best' and 'knew it couldn't'.");
console.log("=".repeat(65));
console.log();
process.exit(0);