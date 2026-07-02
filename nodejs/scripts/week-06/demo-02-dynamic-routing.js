/**
 * Demo 2: Dynamic Routing — model decides the next step
 *
 * Run: node scripts/week-06/demo-02-dynamic-routing.js
 * Requires MCP server running: node src/mcp_server.js
 */
import { runDynamicAgent } from "../../src/agent.js";

console.log("=".repeat(60));
console.log("  Demo 2: Dynamic Routing — model plans at runtime");
console.log("=".repeat(60));
console.log();

const queries = [
  "Is the auth-service healthy?",
  "What was deployed recently?",
  "Are there any incidents?",
];

for (const q of queries) {
  console.log(`  Query: "${q}"`);
  const result = await runDynamicAgent(q);
  console.log(`  Report: ${result.report.slice(0, 150)}...`);
  console.log(`  Steps: ${result.steps}, Cost: $${result.cost.toFixed(6)}`);
  console.log();
}

console.log("  Each query triggered a different path — the model decided.");
console.log("=".repeat(60));
