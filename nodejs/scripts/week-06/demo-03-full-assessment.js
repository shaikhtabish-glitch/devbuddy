/**
 * Demo 3: Full Assessment — all data sources, one report
 *
 * Run: node scripts/week-06/demo-03-full-assessment.js
 * Requires MCP server running: node src/mcp_server.js
 */
import { runDynamicAgent } from "../../src/agent.js";

console.log("=".repeat(60));
console.log("  Demo 3: Full Assessment — all sources, dynamic path");
console.log("=".repeat(60));
console.log();

const query = "Give me a full assessment of inventory-service readiness";
console.log(`  Query: "${query}"`);
console.log();

const result = await runDynamicAgent(query);
console.log("  Report:");
console.log(result.report);
console.log();
console.log(`  Steps: ${result.steps}, Cost: $${result.cost.toFixed(6)}`);
console.log("=".repeat(60));
