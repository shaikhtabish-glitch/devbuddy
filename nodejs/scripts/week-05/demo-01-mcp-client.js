/**
 * Demo 1: Start the MCP Server & Client (SSE transport)
 *
 * Demonstrates the full Model Context Protocol (MCP) lifecycle:
 * 1. Launches the DevBuddy MCP Server on SSE transport.
 * 2. Launches a programmatic MCP Client.
 * 3. Connects the Client to the Server over HTTP/SSE.
 * 4. Discovers available tools dynamically.
 * 5. Calls a tool to inspect auth-service status.
 *
 * Run: node scripts/week-05/demo-01-mcp-client.js
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

// Helper for clean formatting
function printHeader(text) {
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
  console.log(`  \x1b[1m\x1b[35m${text}\x1b[0m`);
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
}

printHeader("DevBuddy MCP — End-to-End Server & Client Demonstration");
console.log();
console.log("  Step 1: Starting DevBuddy MCP Server (SSE transport)...");

// Launch the server in the background of this process
// This spins up the Express server on port 3001
await import("../../src/mcp_server.js");

console.log("  Server initialized. Waiting 1.5s for socket binding...");
await new Promise((r) => setTimeout(r, 1500));

console.log();
console.log("  Step 2: Initializing MCP Client & Connecting over SSE...");
const transport = new SSEClientTransport(new URL("http://localhost:3001/sse"));
const client = new Client(
  { name: "devbuddy-demo-client", version: "1.0.0" },
  { capabilities: {} }
);

try {
  await client.connect(transport);
  console.log("  \x1b[32m✔ Connected successfully!\x1b[0m Established SSE channel.");
  console.log();

  console.log("  Step 3: Querying Discovered Tools...");
  const response = await client.listTools();
  
  console.log("  Discovered Tools:");
  console.log("  ┌────────────────────────────────────────────────────────────────────────┐");
  for (const tool of response.tools) {
    console.log(`  │ 🛠️  \x1b[1m${tool.name.padEnd(20)}\x1b[0m │ ${tool.description.substring(0, 46).padEnd(46)} │`);
  }
  console.log("  └────────────────────────────────────────────────────────────────────────┘");
  console.log();

  console.log("  Step 4: Executing Tool via MCP client connection...");
  console.log("  Calling: get_build_status({ service_name: 'auth-service' })");
  
  const result = await client.callTool({
    name: "get_build_status",
    arguments: { service_name: "auth-service" },
  });

  console.log("  \x1b[32m✔ Tool Execution Result Received:\x1b[0m");
  console.log("  ┌────────────────────────────────────────────────────────────────────────┐");
  const payload = JSON.stringify(JSON.parse(result.content[0].text), null, 2);
  for (const line of payload.split("\n")) {
    console.log(`  │   ${line.padEnd(72)} │`);
  }
  console.log("  └────────────────────────────────────────────────────────────────────────┘");
  console.log();

} catch (e) {
  console.error("  ❌ Client execution failed:", e.message);
} finally {
  console.log("  Step 5: Tearing down client session...");
  await client.close();
  console.log("  Client connection closed. Exiting process.");
  console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
  process.exit(0);
}
