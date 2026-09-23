/**
 * Demo 2: Advanced Client Patterns (Real Implementation)
 *
 * THE POINT OF THIS DEMO:
 * We don't just simulate Progressive Tool Discovery — we actually build it.
 * The LLM starts with only ONE tool (`search_tools`).
 * When it searches, our client intercepts the search, queries the MCP
 * server's cached tool list, dynamically converts the matched MCP JSON
 * schemas into LangChain tools, binds them to the LLM on the fly, and
 * resumes the loop.
 *
 * Prerequisites:
 *   MCP server running in another terminal:
 *     node src/mcp_server.js
 *
 * Run: node scripts/week-05/demo-02-client-scaling.js
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { z } from "zod";
import { DynamicStructuredTool, tool } from "@langchain/core/tools";
import { HumanMessage, SystemMessage, ToolMessage } from "@langchain/core/messages";
import { getLlm } from "../../src/llm.js";
import { BORDER, MCP_URL, REQUEST_OPTS, sleep } from "./_common.js";

/** Convert an MCP JSON schema into a Zod object schema. */
function mcpSchemaToZod(name, schema) {
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
    shape[propName] = required.has(propName)
      ? field
      : field.optional().nullable();
  }
  return z.object(shape);
}

async function main() {
  console.log(BORDER);
  console.log("  Demo 2: Real Progressive Tool Discovery (Client Scaling)");
  console.log(BORDER);
  console.log();

  const transport = new SSEClientTransport(new URL(MCP_URL));
  const client = new Client(
    { name: "devbuddy-demo-client", version: "1.0.0" },
    { capabilities: {} }
  );

  try {
    await client.connect(transport);

    console.log("  [CLIENT] Synchronizing tool registry from Context Server...");
    const mcpTools = (await client.listTools()).tools;
    console.log(
      `  [CLIENT] Discovered ${mcpTools.length} tools. (Imagine this is 10,000 tools in an enterprise).`
    );
    console.log("  [CLIENT] ⚠️ Loading 10,000 JSON schemas would cost ~1.5M tokens per request.");
    console.log("  [CLIENT] 🛡️ Strategy: Starting LLM with ONLY ONE tool -> 'search_tools'.");
    console.log();
    await sleep(1000);

    const activeLcTools = [];

    const searchTools = tool(
      async ({ query }) => {
        console.log(`\n  [CLIENT] Intercepted LLM request to search cache for: '${query}'`);
        const queryWords = query.toLowerCase().split(/\s+/);
        const matches = mcpTools.filter((t) => {
          const nameDesc = `${t.name} ${t.description || ""}`.toLowerCase();
          return queryWords.some((w) => nameDesc.includes(w));
        });

        if (matches.length === 0) {
          return "No tools found matching your query.";
        }

        const names = [];
        for (const mt of matches) {
          if (activeLcTools.some((t) => t.name === mt.name)) continue;

          const argsSchema = mcpSchemaToZod(mt.name, mt.inputSchema || {});
          const st = new DynamicStructuredTool({
            name: mt.name,
            description: mt.description || mt.name,
            schema: argsSchema,
            func: async (kwargs) => {
              console.log(
                `\n  [CLIENT] Passing tool execution to Server: ${mt.name}(${JSON.stringify(kwargs)})`
              );
              const res = await client.callTool({ name: mt.name, arguments: kwargs }, undefined, REQUEST_OPTS);
              return res.content?.[0]?.text ?? "Success";
            },
          });
          activeLcTools.push(st);
          names.push(mt.name);

          // Print the schema injection for visual proof!
          console.log(
            `  [CLIENT] 💉 DYNAMIC INJECTION: Binding schema for '${mt.name}' to LLM context:`
          );
          console.log("  " + "-".repeat(50));
          for (const line of JSON.stringify(mt.inputSchema, null, 2).split("\n")) {
            console.log(`  ${line}`);
          }
          console.log("  " + "-".repeat(50));
        }

        return `Found and loaded schemas for: ${names}. You can now call them directly in your next turn.`;
      },
      {
        name: "search_tools",
        description:
          "Search for available tools on the server and automatically load their schemas.",
        schema: z.object({ query: z.string().describe("What capability you are looking for") }),
      }
    );

    activeLcTools.push(searchTools);
    const llm = getLlm({ temperature: 0 });

    const messages = [
      new SystemMessage(
        "You are an agent. You start with NO domain tools loaded. You MUST use " +
          "`search_tools` to find what you need. After searching, the schemas " +
          "will be loaded and you can call them."
      ),
      new HumanMessage("What is the build status of the payment-api?"),
    ];

    console.log("  [INPUT]: What is the build status of the payment-api?");
    console.log("  ── LLM Orchestration Loop (Turn 1) ─────────────────");
    await sleep(1000);

    for (let turn = 1; turn <= 5; turn++) {
      if (turn > 1) {
        console.log(`  ── LLM Orchestration Loop (Turn ${turn}) ─────────────────`);
      }

      const boundLlm = llm.bindTools(activeLcTools);

      console.log("  [LLM] Thinking...");
      const response = await boundLlm.invoke(messages);
      messages.push(response);

      if (!response.tool_calls || response.tool_calls.length === 0) {
        console.log(`\n  [OUTPUT]: ${response.content}`);
        break;
      }

      for (const tc of response.tool_calls) {
        console.log(`  [LLM] Decided to use tool: ${tc.name}(${JSON.stringify(tc.args)})`);
        const toolObj = activeLcTools.find((t) => t.name === tc.name);
        const res = await toolObj.invoke(tc.args);
        if (tc.name !== "search_tools") {
          console.log(`  [SERVER] Result: ${String(res).trim()}`);
        }
        messages.push(new ToolMessage({ content: String(res), tool_call_id: tc.id }));
      }
      console.log();
      await sleep(1500);
    }

    console.log();
    console.log(BORDER);
    console.log("  THE PAYOFF: We just proved that an AI can navigate an infinitely");
    console.log("  large API surface by dynamically searching, discovering, and");
    console.log("  binding heavy JSON schemas to itself AT RUNTIME, saving millions");
    console.log("  of tokens per request.");
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
