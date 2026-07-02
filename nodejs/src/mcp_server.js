/**
 * Week 5 — MCP Server: Shared Tool Ecosystem (Node.js)
 *
 * Exposes tools over the Model Context Protocol. Each tool retrieves data
 * from the Week 3 RAG index (Qdrant) and synthesises it with the LLM —
 * no hardcoded mock data.
 *
 * Imports: from "./rag.js" (retrieve, indexDocuments)
 *          from "./llm.js" (getLlm)
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { retrieve, indexDocuments } from "./rag.js";
import { getLlm } from "./llm.js";

// ── Startup: ensure the RAG index exists ──────────────────────

try {
  const count = await indexDocuments();
  console.error(`RAG index ready: ${count} chunks indexed`);
} catch (e) {
  console.error(`WARNING: Could not index documents — ${e.message}`);
  console.error("Make sure Qdrant is running: docker compose up -d");
}

// ── Helper: retrieve + synthesise ─────────────────────────────

async function synthesise(instructions, query, k = 5) {
  try {
    const chunks = await retrieve(query, k);
    const context = chunks.length > 0 ? chunks.join("\n\n---\n\n") : "(no data found)";

    const llm = getLlm({ temperature: 0 });
    const response = await llm.invoke([
      new SystemMessage(
        "You are a data extraction tool. " +
          "Only use data present in the provided context. Do not invent information. " +
          "Return ONLY valid JSON (object or array) — no markdown, no prose.\n\n" +
          'If no relevant data is found, return: {"status": "unknown", "reason": "no matching data found"}.\n\n' +
          instructions
      ),
      new HumanMessage(`Context:\n${context}`),
    ]);

    let text = response.content.trim();
    // Strip markdown fences
    if (text.startsWith("```")) {
      text = text.split("\n").slice(1).join("\n");
      if (text.endsWith("```")) text = text.slice(0, -3).trim();
    }
    // Validate
    try {
      JSON.parse(text);
      return { content: [{ type: "text", text }] };
    } catch {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              status: "unknown",
              reason: "could not parse tool result",
            }),
          },
        ],
      };
    }
  } catch (e) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            status: "unknown",
            reason: `tool error: ${e.constructor.name} — ${e.message}`,
          }),
        },
      ],
    };
  }
}

// ── Server + tools ────────────────────────────────────────────

const server = new Server(
  {
    name: "devbuddy-mcp",
    version: "0.1.0",
  },
  {
    capabilities: { tools: {} },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "get_build_status",
      description:
        "Return the current build/health status for a given service. " +
        "Searches the RAG index for build status, health checks, and deployment data. " +
        "Returns a JSON string with status (healthy/degraded/down/unknown) and last_deploy timestamp.",
      inputSchema: {
        type: "object",
        properties: {
          service_name: {
            type: "string",
            description: "The name of the service to check",
          },
        },
        required: ["service_name"],
      },
    },
    {
      name: "get_recent_deploys",
      description:
        "Return the last N deployments for a given service. " +
        "Searches the RAG index for deployment history. " +
        "Returns a JSON array of deploy objects with sha, author, timestamp, status.",
      inputSchema: {
        type: "object",
        properties: {
          service_name: {
            type: "string",
            description: "The name of the service to check",
          },
          limit: {
            type: "number",
            description: "Max number of deploys to return (default 5)",
          },
        },
        required: ["service_name"],
      },
    },
    {
      name: "get_active_incidents",
      description:
        "Return any active (unresolved) incidents for a given service. " +
        "Searches the RAG index for incident reports. " +
        "Returns a JSON array of incident objects with id, severity, date, summary, status.",
      inputSchema: {
        type: "object",
        properties: {
          service_name: {
            type: "string",
            description: "The name of the service to check",
          },
        },
        required: ["service_name"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "get_build_status":
      return await synthesise(
        "Extract the current build/health status for the given service. " +
          "Return JSON with 'status' (one of: healthy, degraded, down, unknown) " +
          "and 'last_deploy' (ISO timestamp). " +
          "Look for the MOST RECENT deployment by date. " +
          "If the most recent deploy was 'success', status = healthy. " +
          "If the most recent deploy was 'rolling_back' or 'failed', status = degraded. " +
          "If no build/health data is found, status = unknown.",
        `${args.service_name} build status health check deploy`
      );

    case "get_recent_deploys":
      return await synthesise(
        "Extract ONLY deployment history for the given service. " +
          "Return a JSON array of deploys, each with: " +
          "sha, author, timestamp, status (success/failed/rolling_back). " +
          "Sort by timestamp descending (most recent first). " +
          `Return at most ${args.limit || 5} entries. ` +
          "If no deployment data is found, return an empty array [].",
        `${args.service_name} deployment history deploy`
      );

    case "get_active_incidents":
      return await synthesise(
        "Extract ONLY active (unresolved) incidents for the given service. " +
          "Return a JSON array of incidents, each with: " +
          "id, severity, date, summary, status (investigating/resolved). " +
          "Skip incidents with status 'resolved' — only include active ones. " +
          "If no incidents are found, return an empty array [].",
        `${args.service_name} incident outage alert`
      );

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// ── Entry point — SSE transport (long-lived daemon) ──────────

async function main() {
  const app = (await import("express")).default();
  const PORT = process.env.MCP_PORT || 3001;

  app.get("/sse", async (req, res) => {
    const transport = new SSEServerTransport("/messages", res);
    await server.connect(transport);
  });

  app.post("/messages", async (req, res) => {
    // SSE transport handles message posting internally
    res.status(200).end();
  });

  app.listen(PORT, () => {
    console.error(`DevBuddy MCP server running on http://localhost:${PORT}/sse`);
  });
}

main().catch((err) => {
  console.error("MCP server failed:", err);
  process.exit(1);
});
