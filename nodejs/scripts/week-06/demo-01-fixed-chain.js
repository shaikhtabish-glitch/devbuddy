/**
 * Demo 1: Fixed Chain — 4-step deterministic pipeline
 *
 * Run: node scripts/week-06/demo-01-fixed-chain.js
 * Requires MCP server running: node src/mcp_server.js
 */
import { runFixedChain } from "../../src/agent.js";

console.log("=".repeat(60));
console.log("  Demo 1: Fixed Chain — extract → retrieve → build → report");
console.log("=".repeat(60));
console.log();

const query = "Is the payment-api ready for release?";
console.log(`  Query: "${query}"`);
console.log();

const result = await runFixedChain(query);
console.log("  Report:");
console.log(result.report);
console.log();
console.log(`  Steps: ${result.steps}, Cost: $${result.cost.toFixed(6)}`);
console.log("=".repeat(60));
process.exit(0);
