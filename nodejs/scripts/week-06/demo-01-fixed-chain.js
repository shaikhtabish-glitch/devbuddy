/**
 * Demo 1 (C1): Fixed Chain — a state machine, not a for-loop
 *
 * buildFixedChain() compiles nodes + hardcoded edges into a LangGraph
 * runtime. We STREAM it: the graph drives node → node, and after every
 * transition you see which state fields the node filled — and which are
 * still empty (that emptiness is the fuel for C2, demo-04).
 *
 * Requires: MCP server (node src/mcp_server.js, :3001) + Qdrant (:6333)
 * Run: node scripts/week-06/demo-01-fixed-chain.js
 */
import { buildFixedChain, initState, formatReport } from "../../src/agent.js";

const DATA_FIELDS = [
  "service_name",
  "context",
  "build_status",
  "deploys",
  "incidents",
  "report",
];

const empty = (v) => v === null || v === undefined || v === "";

function traceFixedChain(query) {
  return (async () => {
    const state = initState(query);
    console.log(`  📥  QUERY: "${query}"`);
    console.log(`  ${"─".repeat(59)}`);

    const agent = buildFixedChain(); // compile(): nodes + edges → runnable graph
    // edges (hardcoded — THIS is what "fixed" means):
    //   extract_service → retrieve → check_build → generate_report → END

    let seenEvents = 0;
    for await (const event of await agent.stream(state)) {
      for (const [nodeName, update] of Object.entries(event)) {
        Object.assign(state, update);

        const nodeEvents = state.messages.slice(seenEvents);
        seenEvents = state.messages.length;
        const filled = DATA_FIELDS.filter((k) => !empty(state[k]));
        const pending = DATA_FIELDS.filter((k) => empty(state[k]));

        console.log(`  ▶ ${nodeName}`);
        for (const audit of nodeEvents) {
          const { step, cost, ...detail } = audit;
          const costStr = cost ? `  · $${cost.toFixed(6)}` : "";
          console.log(`      audit      : ${JSON.stringify(detail)}${costStr}`);
        }
        console.log(`      filled     : ${filled.join(", ") || "—"}`);
        console.log(
          `      still empty: ${pending.join(", ") || "—"}` +
            (pending ? "   ← a node that never fills these = C2 (demo-04)" : "")
        );
        console.log();
      }
    }

    console.log(`  ${"─".repeat(59)}`);
    console.log(`  📤  REPORT (structured AgentAnswer — Week 2 contract):`);
    console.log(formatReport(state.report));
    console.log();
    console.log(`  🧾  AUDIT TRAIL (recorded by the nodes, with per-step cost):`);
    for (const m of state.messages) console.log(`          • ${JSON.stringify(m)}`);
    console.log(
      `  ⚡  TOTAL: ${state.steps} steps · $${state.cost.toFixed(6)}`
    );
    console.log();
  })();
}

console.log();
console.log("=".repeat(65));
console.log("  Demo 1 (C1): Fixed Chain — the graph drives the transitions");
console.log("=".repeat(65));
console.log();
console.log("  Nodes are functions. Edges are hardcoded. The RUNTIME walks");
console.log("  them — nothing below is a hand-written for-loop.");
console.log();

await traceFixedChain("Is the payment-api ready for v2.1?");
await traceFixedChain("Is the auth-service ready for release?");

console.log("=".repeat(65));
console.log("  Fixed chain: same edges, same order, both queries — 4 nodes.");
console.log("  🔀  extract → retrieve → check_build → generate_report → END");
console.log("  Predictable and auditable, but it CANNOT skip a step or add");
console.log("  one (no deploys/incidents nodes here). See demo-02 for a graph");
console.log("  whose edges are chosen at runtime.");
console.log("=".repeat(65));
console.log();
process.exit(0);