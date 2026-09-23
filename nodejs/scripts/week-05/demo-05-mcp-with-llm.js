/**
 * Demo 5: The Ecosystem Payoff — Prompts, Resources, and Tools
 *
 * THE POINT OF THIS DEMO: The grand finale. The LLM acts as the orchestrator.
 * It doesn't use hardcoded system prompts. It asks the Server for the Prompt.
 * It asks the Server for the Resource.
 * It asks the Server for the Tools.
 * Then it executes the workflow.
 *
 * Prerequisites:
 *   Qdrant running (Week 3)
 *   MCP server running on port 3001:
 *     node src/mcp_server.js
 *
 * Run: node scripts/week-05/demo-05-mcp-with-llm.js
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { z } from "zod";
import { DynamicStructuredTool } from "@langchain/core/tools";
import { HumanMessage, SystemMessage, ToolMessage } from "@langchain/core/messages";
import { getLlm } from "../../src/llm.js";
import { BORDER, MCP_URL, REQUEST_OPTS } from "./_common.js";

/** Convert an MCP JSON schema into a Zod object schema. */
function mcpSchemaToZod(schema) {
  const shape = {};
  const properties = schema?.properties || {};
  const required = new Set(schema?.required || []);
  for (const [propName, propInfo] of Object.entries(properties)) {
    let field;
    switch (propInfo.type) {
      case "integer":
        field = z.number().int();
        break;
      case "number":
        field = z.number();
        break;
      case "boolean":
        field = z.boolean();
        break;
      case "array":
        field = z.array(z.any());
        break;
      case "object":
        field = z.record(z.any());
        break;
      default:
        field = z.string();
    }
    if (propInfo.description) field = field.describe(propInfo.description);
    shape[propName] = required.has(propName) ? field : field.optional().nullable();
  }
  return z.object(shape);
}

async function main() {
  console.log(BORDER);
  console.log("  Demo 5: The Ecosystem Payoff");
  console.log(BORDER);
  console.log();

  const transport = new SSEClientTransport(new URL(MCP_URL));
  const client = new Client(
    { name: "devbuddy-demo-client", version: "1.0.0" },
    { capabilities: {} }
  );

  try {
    await client.connect(transport);

    // 1. Get Prompt
    console.log("  ── 1. Fetching Server Prompt ───────────────────────");
    const service = "payment-api";
    const promptData = await client.getPrompt({
      name: "incident_analysis_prompt",
      arguments: { service_name: service },
    });
    const systemText = promptData.messages[0].content.text;
    console.log(`  Received: '${systemText.slice(0, 70)}...'`);
    console.log();

    // 2. Get Resource
    console.log("  ── 2. Fetching Server Resource ─────────────────────");
    let resourceText;
    try {
      const resData = await client.readResource(
        { uri: "file://shared/data/payment-api-spec.md" },
        REQUEST_OPTS
      );
      resourceText = `${resData.contents[0].text.slice(0, 100)}...`;
    } catch {
      resourceText = "(Resource unavailable)";
    }
    console.log(`  Received: '${resourceText}'`);
    console.log();

    // 3. Get Tools
    console.log("  ── 3. Fetching Server Tools ────────────────────────");
    const mcpTools = (await client.listTools()).tools;
    const lcTools = mcpTools.map(
      (mt) =>
        new DynamicStructuredTool({
          name: mt.name,
          description: mt.description || mt.name,
          schema: mcpSchemaToZod(mt.inputSchema || {}),
          func: async (kwargs) => {
            const res = await client.callTool(
              { name: mt.name, arguments: kwargs },
              undefined,
              REQUEST_OPTS
            );
            return res.content?.[0]?.text ?? "";
          },
        })
    );
    console.log(`  Bound ${lcTools.length} tools to LLM.`);
    console.log();

    // 4. Execute
    console.log("  ── 4. LLM Execution Loop ───────────────────────────");
    const llm = getLlm({ temperature: 0 }).bindTools(lcTools);

    // The context is assembled purely from the server!
    const messages = [
      new SystemMessage(systemText),
      new HumanMessage(
        `Here is the API Spec Resource: ${resourceText}\n\nPlease proceed with the analysis.`
      ),
    ];

    for (let turn = 0; turn < 4; turn++) {
      const response = await llm.invoke(messages);
      messages.push(response);

      if (!response.tool_calls || response.tool_calls.length === 0) {
        console.log(`  [Final Answer]:\n  ${response.content}`);
        break;
      }

      for (const tc of response.tool_calls) {
        console.log(`  [Model Decided]: Call ${tc.name}(${JSON.stringify(tc.args)})`);
        const result = await client.callTool(
          { name: tc.name, arguments: tc.args },
          undefined,
          REQUEST_OPTS
        );
        const resultText = result.content?.[0]?.text ?? "no result";
        messages.push(new ToolMessage({ content: resultText, tool_call_id: tc.id }));
      }
    }

    console.log();
    console.log(BORDER);
    console.log("  THE MESSAGE: The client is completely generic. The Prompts,");
    console.log("  Resources, and Tools all lived on the server. We have achieved");
    console.log("  true separation of Context from the Application layer.");
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
