/**
 * Week 5 — MCP Server: Shared Tool Ecosystem (Node.js)
 *
 * Exposes tools, resources, and prompts over the Model Context Protocol.
 * Each tool retrieves data from the Week 3 RAG index (Qdrant) and
 * synthesises it with the LLM — no hardcoded mock data.
 *
 *   [Tools]      get_build_status / get_recent_deploys / get_active_incidents
 *                + delete_incident_record (destructive, token-gated)
 *   [Resources]  file://shared/data/{filename} — read shared markdown docs
 *   [Prompts]    incident_analysis_prompt — standard SRE workflow
 *
 * Imports: from "./rag.js" (retrieve, indexDocuments)
 *          from "./llm.js" (getLlm)
 */
import { readFileSync } from "fs";
import { resolve, dirname, basename } from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ListResourceTemplatesRequestSchema,
  ReadResourceRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { retrieve, indexDocuments } from "./rag.js";
import { getLlm } from "./llm.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SHARED_DATA_DIR = resolve(__dirname, "..", "..", "shared", "data");
const RESOURCE_URI_PREFIX = "file://shared/data/";
const ADMIN_TOKEN = "super-secret-approval-123";

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

// ── Rate limiting (real, stateful) ────────────────────────────

const _rateLimits = new Map();

/**
 * Enforce a per-tool sliding window. Throws a RateLimitExceeded error when
 * the caller exceeds `limit` calls within `windowSeconds`.
 */
export function checkRateLimit(toolName, limit = 3, windowSeconds = 10) {
  const now = Date.now();
  const state = _rateLimits.get(toolName) || { count: 0, windowStart: now };

  if (now - state.windowStart > windowSeconds * 1000) {
    state.count = 1;
    state.windowStart = now;
  } else {
    state.count += 1;
    if (state.count > limit) {
      const err = new Error(
        `RateLimitExceeded: Tool '${toolName}' called too many times. ` +
          `Limit ${limit} per ${windowSeconds}s.`
      );
      err.name = "RateLimitExceeded";
      throw err;
    }
  }
  _rateLimits.set(toolName, state);
}

/** Test helper — clear all rate-limit windows. */
export function resetRateLimits() {
  _rateLimits.clear();
}

// ── Tool definitions (the schema the client discovers) ────────

export const TOOL_DEFINITIONS = [
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
    name: "delete_incident_record",
    description:
      "DESTRUCTIVE TOOL: Delete an incident record. " +
      "Requires an out-of-band admin_token to simulate Human-In-The-Loop approval.",
    inputSchema: {
      type: "object",
      properties: {
        incident_id: {
          type: "string",
          description: "The incident ID to delete (e.g. INC-123)",
        },
        admin_token: {
          type: "string",
          description: "Out-of-band approval token (Human-In-The-Loop)",
        },
      },
      required: ["incident_id", "admin_token"],
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
];

// ── Tool handlers ─────────────────────────────────────────────

const TOOL_HANDLERS = {
  async get_build_status(args) {
    checkRateLimit("get_build_status", 3, 30);
    return synthesise(
      "Extract the current build/health status for the given service. " +
        "Return JSON with 'status' (one of: healthy, degraded, down, unknown) " +
        "and 'last_deploy' (ISO timestamp). " +
        "Look for the MOST RECENT deployment by date. " +
        "If the most recent deploy was 'success', status = healthy. " +
        "If the most recent deploy was 'rolling_back' or 'failed', status = degraded. " +
        "If no build/health data is found, status = unknown.",
      `${args.service_name} build status health check deploy`
    );
  },

  async delete_incident_record(args) {
    if (args.admin_token !== ADMIN_TOKEN) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              status: "error",
              reason: "Unauthorized. Invalid admin_token.",
            }),
          },
        ],
      };
    }
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: "success", deleted: args.incident_id }),
        },
      ],
    };
  },

  async get_recent_deploys(args) {
    return synthesise(
      "Extract ONLY deployment history for the given service. " +
        "Return a JSON array of deploys, each with: " +
        "sha, author, timestamp, status (success/failed/rolling_back). " +
        "Sort by timestamp descending (most recent first). " +
        `Return at most ${args.limit || 5} entries. ` +
        "If no deployment data is found, return an empty array [].",
      `${args.service_name} deployment history deploy`
    );
  },

  async get_active_incidents(args) {
    return synthesise(
      "Extract ONLY active (unresolved) incidents for the given service. " +
        "Return a JSON array of incidents, each with: " +
        "id, severity, date, summary, status (investigating/resolved). " +
        "Skip incidents with status 'resolved' — only include active ones. " +
        "If no incidents are found, return an empty array [].",
      `${args.service_name} incident outage alert`
    );
  },
};

// ── Resources ─────────────────────────────────────────────────

/** Static resources. The server exposes a template, not fixed files. */
export function listSharedResources() {
  return [];
}

/** Resource templates — the filesystem the client may navigate. */
export function listSharedResourceTemplates() {
  return [
    {
      uriTemplate: `${RESOURCE_URI_PREFIX}{filename}`,
      name: "shared_document",
      description: "Read a document from the shared/data directory.",
      mimeType: "text/markdown",
    },
  ];
}

/**
 * Read a document from shared/data. Rejects anything that escapes the
 * template prefix or attempts path traversal.
 */
export function readSharedResource(uri) {
  if (!uri || !uri.startsWith(RESOURCE_URI_PREFIX)) {
    throw new Error(`Resource not found: ${uri}`);
  }
  const raw = uri.slice(RESOURCE_URI_PREFIX.length);
  const filename = basename(raw);
  if (!filename || filename !== raw || raw.includes("/") || raw.includes("..")) {
    throw new Error(`Resource not found: ${uri}`);
  }
  const filepath = resolve(SHARED_DATA_DIR, filename);
  if (!filepath.startsWith(SHARED_DATA_DIR)) {
    throw new Error(`Resource not found: ${uri}`);
  }
  const text = readFileSync(filepath, "utf-8");
  return { uri, mimeType: "text/markdown", text };
}

// ── Prompts ───────────────────────────────────────────────────

export const PROMPT_DEFINITIONS = [
  {
    name: "incident_analysis_prompt",
    description: "A standard prompt for analyzing service incidents.",
    arguments: [
      {
        name: "service_name",
        description: "The service to analyze (e.g. payment-api)",
        required: true,
      },
    ],
  },
];

/** Build the incident-analysis prompt for a service. */
export function getIncidentAnalysisPrompt(serviceName) {
  const text =
    `You are a Site Reliability Engineer. Analyze the recent incidents ` +
    `and deployments for ${serviceName}. Use the 'get_active_incidents' ` +
    `and 'get_recent_deploys' tools to gather data. ` +
    `Also read the SLA resource for the service if available. ` +
    `Provide a root cause hypothesis and an action plan.`;
  return {
    description: `Incident analysis workflow for ${serviceName}`,
    messages: [{ role: "user", content: { type: "text", text } }],
  };
}

// ── Server factory ────────────────────────────────────────────

/** Build a fully-wired MCP server (without binding a transport). */
export function createServer() {
  const server = new Server(
    {
      name: "devbuddy-mcp",
      version: "0.1.0",
    },
    {
      capabilities: { tools: {}, resources: {}, prompts: {} },
    }
  );

  // Tools
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOL_DEFINITIONS,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const handler = TOOL_HANDLERS[name];
    if (!handler) {
      // Unknown tool = protocol error (client must re-plan via list_tools).
      throw new Error(`Unknown tool: ${name}`);
    }
    try {
      return await handler(args || {});
    } catch (e) {
      // A tool that throws during execution → structured error result.
      return {
        content: [{ type: "text", text: `${e.name || "Error"}: ${e.message}` }],
        isError: true,
      };
    }
  });

  // Resources
  server.setRequestHandler(ListResourcesRequestSchema, async () => ({
    resources: listSharedResources(),
  }));

  server.setRequestHandler(ListResourceTemplatesRequestSchema, async () => ({
    resourceTemplates: listSharedResourceTemplates(),
  }));

  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const content = readSharedResource(request.params.uri);
    return { contents: [content] };
  });

  // Prompts
  server.setRequestHandler(ListPromptsRequestSchema, async () => ({
    prompts: PROMPT_DEFINITIONS,
  }));

  server.setRequestHandler(GetPromptRequestSchema, async (request) => {
    const { name, arguments: args = {} } = request.params;
    if (name !== "incident_analysis_prompt") {
      throw new Error(`Unknown prompt: ${name}`);
    }
    return getIncidentAnalysisPrompt(args.service_name || "unknown-service");
  });

  return server;
}

// ── Entry point — SSE transport (long-lived daemon) ──────────

export async function main() {
  const express = (await import("express")).default;
  const app = express();
  const server = createServer();

  const PORT = process.env.MCP_PORT || 3001;
  const transports = {};

  app.get("/sse", async (req, res) => {
    const transport = new SSEServerTransport("/messages", res);
    transports[transport.sessionId] = transport;

    res.on("close", () => {
      delete transports[transport.sessionId];
    });

    await server.connect(transport);
  });

  app.post("/messages", async (req, res) => {
    const sessionId = req.query.sessionId;
    const transport = transports[sessionId];

    if (transport) {
      await transport.handlePostMessage(req, res);
    } else {
      res.status(400).send("No transport found for sessionId");
    }
  });

  app.listen(PORT, () => {
    console.error(`DevBuddy MCP server running on http://localhost:${PORT}/sse`);
  });
}

// Only start the HTTP server when run directly — importing the module
// (e.g. in tests) must not bind a port.
const isMain =
  process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  main().catch((err) => {
    console.error("MCP server failed:", err);
    process.exit(1);
  });
}
