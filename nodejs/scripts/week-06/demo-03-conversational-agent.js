/**
 * Demo 3: Conversational Agent — talk to DevBuddy
 *
 * Type queries. The dynamic agent plans, calls tools, and responds.
 * Type 'quit' to exit, 'cost' to see cumulative spending.
 *
 * Requires: MCP server running (node src/mcp_server.js in another terminal)
 * Run: node scripts/week-06/demo-03-conversational-agent.js
 */
import { createInterface } from "readline";
import { runDynamicAgent } from "../../src/agent.js";

console.log("=".repeat(70));
console.log("  DevBuddy Agent — Conversational Mode");
console.log("=".repeat(70));
console.log();
console.log("  I can check build status, deployment history, active");
console.log("  incidents, and retrieve documentation. Ask me anything");
console.log("  about auth-service, payment-api, or inventory-service.");
console.log();
console.log("  Commands:  quit  |  cost  |  help");
console.log();

const rl = createInterface({ input: process.stdin, output: process.stdout });
let totalCost = 0.0;
let turn = 0;

async function ask() {
  rl.question("  You → ", async (query) => {
    query = query.trim();
    if (!query) return ask();
    if (["quit", "exit", "q"].includes(query.toLowerCase())) {
      console.log();
      console.log(`  Session ended. ${turn} queries, total cost ~$${totalCost.toFixed(6)}`);
      console.log("=".repeat(70));
      rl.close();
      return;
    }
    if (query.toLowerCase() === "cost") {
      console.log(`  💰 Total cost this session: ~$${totalCost.toFixed(6)}`);
      console.log();
      return ask();
    }
    if (query.toLowerCase() === "help") {
      console.log("  Try: 'Is payment-api healthy?'");
      console.log("       'What was deployed recently for auth-service?'");
      console.log("       'Any incidents for inventory-service?'");
      console.log("       'Give me a full readiness report for payment-api'");
      console.log();
      return ask();
    }

    turn++;
    console.log(`  ⏳ Turn ${turn} — planning and executing...`);
    const result = await runDynamicAgent(query);
    totalCost += result.cost || 0;

    console.log(`  Steps: ${result.steps}  |  Cost: ~$${(result.cost || 0).toFixed(6)}`);
    console.log("  ─────────────────────────────────────────────");
    console.log(`  ${result.report}`);
    console.log();
    ask();
  });
}

ask();
