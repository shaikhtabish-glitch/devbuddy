/**
 * Demo 3: Protocol Errors & Resilience
 *
 * THE POINT OF THIS DEMO: MCP connections fail in predictable ways.
 * Since you are now requesting Context over a network, you must handle
 * network errors, missing resources, and missing tools.
 * These are operational patterns, not bugs.
 *
 * Prerequisites:
 *   MCP server running on port 3001:
 *     node src/mcp_server.js
 *
 * Run: node scripts/week-05/demo-03-break-it.js
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { BORDER, MCP_URL, REQUEST_OPTS, pause, printError } from "./_common.js";

async function withClient(url, fn) {
  const transport = new SSEClientTransport(new URL(url));
  const client = new Client(
    { name: "devbuddy-demo-client", version: "1.0.0" },
    { capabilities: {} }
  );
  await client.connect(transport);
  try {
    await fn(client);
  } finally {
    await client.close().catch(() => {});
  }
}

async function main() {
  console.log(BORDER);
  console.log("  Demo 3: Protocol Errors & Resilience");
  console.log(BORDER);
  console.log();
  console.log("  When you shift to an ecosystem model, failure handling moves");
  console.log("  from Try/Catch blocks to Application Layer Routing.");
  console.log();

  // ── Act 1: Resource Not Found ──────────────────────────────────
  console.log("  ── Act 1: Requesting a missing Resource ──────────────────");
  console.log("  Client asks for a file that isn't exposed or doesn't exist.");
  console.log();

  const targetUri = "file:///etc/passwd";
  console.log(`  [INPUT]  → client.readResource({ uri: '${targetUri}' })`);

  try {
    await withClient(MCP_URL, async (client) => {
      await client.readResource({ uri: targetUri }, REQUEST_OPTS);
      console.log("  [OUTPUT] ← ❓ Unexpected success");
      console.log();
    });
  } catch (e) {
    printError(e);
  }

  console.log("  KEY INSIGHT: The server explicitly rejected this. Path traversal");
  console.log("  is blocked by the protocol mapping.");
  console.log();
  await pause();

  // ── Act 2: Tool Not Found ──────────────────────────────────────
  console.log("  ── Act 2: Requesting a missing Tool ──────────────────────");
  console.log("  Client attempts to execute a legacy tool name.");
  console.log();

  const toolName = "get_buildstatus"; // intentionally misspelled
  const toolArgs = { service_name: "auth-service" };
  console.log(`  [INPUT]  → client.callTool({ name: '${toolName}', arguments: ${JSON.stringify(toolArgs)} })`);

  try {
    await withClient(MCP_URL, async (client) => {
      await client.callTool({ name: toolName, arguments: toolArgs }, undefined, REQUEST_OPTS);
      console.log("  [OUTPUT] ← ❓ Unexpected success");
      console.log();
    });
  } catch (e) {
    printError(e);
  }

  console.log("  KEY INSIGHT: Unknown tool errors come from the SERVER.");
  console.log("  The client must gracefully handle this and perhaps ask the LLM");
  console.log("  to re-plan using `listTools()`.");
  console.log();
  await pause();

  // ── Act 3: Connection Error ────────────────────────────────────
  console.log("  ── Act 3: Server Offline ─────────────────────────────────");
  console.log("  Client attempts to connect to a server that isn't running.");
  console.log();

  const badUrl = "http://127.0.0.1:9999/sse";
  console.log(`  [INPUT]  → connecting to '${badUrl}'`);

  try {
    await withClient(badUrl, async () => {
      console.log("  [OUTPUT] ← ❓ Unexpected success");
      console.log();
    });
  } catch (e) {
    printError(e);
  }

  console.log("  KEY INSIGHT: Connection errors happen at the transport layer,");
  console.log("  before MCP even initializes. Your client needs retry logic with");
  console.log("  exponential backoff.");
  console.log();
  await pause();

  console.log(BORDER);
  console.log("  THE MESSAGE: The protocol enforces strict contracts. Your AI orchestrator");
  console.log("  must be built to handle these rejections gracefully, dynamically");
  console.log("  re-querying the context server when resources or tools shift.");
  console.log(BORDER);
}

main()
  .then(() => process.exit(0))
  .catch((e) => {
    console.error(`  ❌ Demo failed: ${e.message}`);
    console.error("  Ensure the MCP server is running:  node src/mcp_server.js");
    process.exit(1);
  });
