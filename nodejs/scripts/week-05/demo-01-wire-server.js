/**
 * Demo 1: Discovering Context (Resources & Prompts)
 *
 * THE POINT OF THIS DEMO: We are going to connect to the MCP server and ask
 * it for Context, not just Tools. We will discover the shared markdown
 * documents (Resources) and standard operational templates (Prompts).
 *
 * Prerequisites:
 *   MCP server running in another terminal:
 *     node src/mcp_server.js
 *
 * Run: node scripts/week-05/demo-01-wire-server.js
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { BORDER, MCP_URL, REQUEST_OPTS, pause, printHeader } from "./_common.js";

async function main() {
  const transport = new SSEClientTransport(new URL(MCP_URL));
  const client = new Client(
    { name: "devbuddy-demo-client", version: "1.0.0" },
    { capabilities: {} }
  );

  try {
    await client.connect(transport);

    printHeader("Demo 1: Discovering Context (Resources & Prompts)");
    console.log();

    // ── Step 1: Discover Resources ─────────────────────────
    console.log("  ── Step 1: Discover Resources ─────────────────────");
    console.log("  Instead of writing a custom tool to read the SLA document,");
    console.log("  the server exposes it as a standard Resource.");
    console.log();

    const resourcesResult = await client.listResources();
    const templatesResult = await client.listResourceTemplates();
    const total =
      resourcesResult.resources.length + templatesResult.resourceTemplates.length;
    console.log(`  Server exposes ${total} resource(s) / template(s):`);

    for (const r of resourcesResult.resources) {
      console.log(`    • [Static] ${r.name} (URI: ${r.uri})`);
    }
    for (const t of templatesResult.resourceTemplates) {
      console.log(`    • [Template] ${t.name} (URI: ${t.uriTemplate})`);
    }
    console.log();

    console.log("  ⏸  Let's read a resource directly via the protocol.");
    await pause();

    // Read a resource
    const targetUri = "file://shared/data/inventory-service-sla.md";
    console.log(`  Reading: ${targetUri}`);
    try {
      const resourceData = await client.readResource({ uri: targetUri }, REQUEST_OPTS);
      const text = resourceData.contents[0].text;
      console.log("  Contents:");
      console.log(`    ${text.trim()}`);
    } catch (e) {
      console.log(`  ❌ Error reading resource: ${e.message}`);
    }
    console.log();

    // ── Step 2: Discover Prompts ───────────────────────────
    console.log("  ── Step 2: Discover Prompts ───────────────────────");
    console.log("  The server also holds the standard playbook for incident analysis.");
    console.log("  The client doesn't need to hardcode the prompt.");
    console.log();

    const promptsResult = await client.listPrompts();
    console.log(`  Server exposes ${promptsResult.prompts.length} prompt(s):`);
    for (const p of promptsResult.prompts) {
      const desc = p.description || "(no description)";
      const args = (p.arguments || []).map((a) => a.name);
      console.log(`    • ${p.name}: ${desc}`);
      console.log(`      Args: ${args.length ? args.join(", ") : "None"}`);
    }
    console.log();

    console.log("  ⏸  Let's fetch the prompt template for 'auth-service'.");
    await pause();

    try {
      const promptData = await client.getPrompt({
        name: "incident_analysis_prompt",
        arguments: { service_name: "auth-service" },
      });
      console.log("  Returned Prompt Message:");
      console.log(`    ${promptData.description}`);
      for (const msg of promptData.messages) {
        if (msg.content.type === "text") {
          console.log(`    Content: ${msg.content.text.slice(0, 80)}...`);
        }
      }
    } catch (e) {
      console.log(`  ❌ Error fetching prompt: ${e.message}`);
    }
    console.log();

    console.log(BORDER);
    console.log("  THE SHIFT: Your client just read a proprietary document and");
    console.log("  fetched an operational workflow without calling a single 'tool'.");
    console.log("  This is Context Engineering.");
    console.log(BORDER);
  } finally {
    await client.close().catch(() => {});
  }
}

main()
  .then(() => process.exit(0))
  .catch((e) => {
    console.error(`  ❌ Demo failed: ${e.message}`);
    console.error("  Ensure the MCP server is running:  node src/mcp_server.js");
    process.exit(1);
  });
