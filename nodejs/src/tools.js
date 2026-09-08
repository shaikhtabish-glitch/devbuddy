/**
 * Week 4 — Tool definitions + function calling (Node.js)
 *
 * Tools are real functions the model can decide to call.
 * The model decides. Your code executes. This boundary is sacred.
 *
 * Design (single source of truth, mirrors python/src/tools.py):
 *   • Raw functions  — buildStatus / recentDeploys / activeIncidents —
 *     own the data. Demos wrap these (e.g. flaky) without duplicating.
 *   • Tool wrappers  — getBuildStatus / getRecentDeploys /
 *     getActiveIncidents — own the schema the model sees. Descriptions
 *     teach routing.
 *
 * Imports: import { getLlm } from "./llm.js"
 */
import { z } from "zod";
import { tool } from "@langchain/core/tools";
import { HumanMessage, SystemMessage, ToolMessage } from "@langchain/core/messages";
import { getLlm } from "./llm.js";

// ═══════════════════════════════════════════════════════════════
// Tool data — mock implementations of live APIs
// ═══════════════════════════════════════════════════════════════

const BUILD_STATUSES = {
  "auth-service": { status: "healthy", last_deploy: "2026-06-28T08:15:00Z" },
  "payment-api": {
    status: "degraded",
    last_deploy: "2026-06-28T06:45:00Z",
    failing_since: "2026-06-28T07:30:00Z",
  },
  "inventory-service": { status: "unknown", last_deploy: "2026-06-20T11:00:00Z" },
};

const DEPLOYS = {
  "auth-service": [
    { sha: "abc123def456", author: "tabish", timestamp: "2026-06-28T08:15:00Z", status: "success" },
    { sha: "789ghi012jkl", author: "alex", timestamp: "2026-06-27T14:30:00Z", status: "success" },
  ],
  "payment-api": [
    { sha: "def789ghi012", author: "maria", timestamp: "2026-06-28T06:45:00Z", status: "success" },
    { sha: "jkl345mno678", author: "maria", timestamp: "2026-06-27T22:00:00Z", status: "rolling_back" },
    { sha: "pqr901stu234", author: "jordan", timestamp: "2026-06-27T20:15:00Z", status: "failed" },
  ],
  "inventory-service": [],
};

const INCIDENTS = {
  "payment-api": [
    {
      id: "INC-842",
      severity: "Sev1",
      summary: "payment-api latency spike. 15% of requests affected. Error code 408.",
      status: "investigating",
    },
  ],
  "auth-service": [],
  "inventory-service": [
    {
      id: "INC-901",
      severity: "Sev3",
      summary: "inventory-service data inconsistency between primary and replica.",
      status: "investigating",
      tracking: ["PROJ-891", "PROJ-892"],
    },
  ],
};

// ═══════════════════════════════════════════════════════════════
// Raw functions — the data sources (wrap these in demos/tests)
// ═══════════════════════════════════════════════════════════════

export async function buildStatus(service_name) {
  const data = BUILD_STATUSES[service_name];
  if (!data) {
    return JSON.stringify({
      status: "unknown",
      error: `No data for service '${service_name}'`,
    });
  }
  return JSON.stringify(data);
}

export async function recentDeploys(service_name, limit = 5) {
  const serviceDeploys = DEPLOYS[service_name] || [];
  return JSON.stringify(serviceDeploys.slice(0, limit), null, 2);
}

export async function activeIncidents(service_name) {
  const serviceIncidents = INCIDENTS[service_name] || [];
  return JSON.stringify(serviceIncidents, null, 2);
}

// ═══════════════════════════════════════════════════════════════
// Tool wrappers — the schemas the model sees (descriptions teach routing)
// ═══════════════════════════════════════════════════════════════

export const getBuildStatus = tool(
  async ({ service_name }) => buildStatus(service_name),
  {
    name: "get_build_status",
    description:
      "Return the current build/health status for a given service. " +
      "Returns a JSON string with status and last deploy timestamp. " +
      "Status is one of: 'healthy', 'degraded', 'down', 'unknown'.",
    schema: z.object({
      service_name: z.string().describe("The name of the service to check"),
    }),
  }
);

export const getRecentDeploys = tool(
  async ({ service_name, limit = 5 }) => recentDeploys(service_name, limit),
  {
    name: "get_recent_deploys",
    description:
      "Return the last N deployments for a given service. " +
      "Each deploy has: sha, author, timestamp, status. " +
      "Status is one of: 'success', 'failed', 'rolling_back'.",
    schema: z.object({
      service_name: z.string().describe("The name of the service to check"),
      limit: z.number().optional().nullable().default(5).describe("Max number of deploys to return"),
    }),
  }
);

export const getActiveIncidents = tool(
  async ({ service_name }) => activeIncidents(service_name),
  {
    name: "get_active_incidents",
    description:
      "Return any active (unresolved) incidents for a given service. " +
      "Returns a JSON list of incident objects with id, severity, and summary.",
    schema: z.object({
      service_name: z.string().describe("The name of the service to check"),
    }),
  }
);

// ═══════════════════════════════════════════════════════════════
// Tool execution — the application layer
// ═══════════════════════════════════════════════════════════════

export const ALL_TOOLS = [getBuildStatus, getRecentDeploys, getActiveIncidents];
export const TOOLS_BY_NAME = Object.fromEntries(ALL_TOOLS.map((t) => [t.name, t]));

// Upper bound on tool-calling rounds. The model may chain tools (status →
// deploys → incidents); if it never settles on a text answer we force one.
// A model that never stops calling tools is a cost event, not a feature.
export const MAX_TOOL_TURNS = 6;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Deterministic failure injection for demos/tests (mirrors python flaky()).
 *
 * Wraps a raw function (e.g. buildStatus) so the first `failFirstN` calls
 * reject and later calls succeed. Each wrapper owns its own counter — no
 * shared global state, no reliance on call order across scenarios.
 */
export function flaky(fn, failFirstN = 0, ErrorCtor = Error) {
  const state = { made: 0 };
  const wrapped = async (...args) => {
    state.made += 1;
    if (state.made <= failFirstN) {
      throw new ErrorCtor(`Simulated failure ${state.made}/${failFirstN}`);
    }
    return fn(...args);
  };
  wrapped.__name = `flaky_${fn.name || "fn"}`;
  return wrapped;
}

function _asText(message) {
  /** Extract plain text from an AI message (handles str or content blocks). */
  const content = message.content;
  if (typeof content === "string") {
    return content.trim();
  }
  if (Array.isArray(content)) {
    return content
      .map((b) => (b && typeof b === "object" ? b.text || "" : String(b)))
      .join("")
      .trim();
  }
  return String(content == null ? "" : content).trim();
}

function _usageOf(message) {
  /** Best-effort token usage from usage_metadata or response_metadata.tokenUsage. */
  const md = message.usage_metadata;
  if (md && (md.input_tokens != null || md.output_tokens != null || md.total_tokens != null)) {
    return {
      input_tokens: md.input_tokens || 0,
      output_tokens: md.output_tokens || 0,
      total_tokens: md.total_tokens || 0,
    };
  }
  const tu = message.response_metadata && message.response_metadata.tokenUsage;
  if (tu) {
    return {
      input_tokens: tu.promptTokens || 0,
      output_tokens: tu.completionTokens || 0,
      total_tokens: tu.totalTokens || 0,
    };
  }
  return { input_tokens: 0, output_tokens: 0, total_tokens: 0 };
}

/**
 * Execute a tool call with error handling in the application layer.
 *
 * Retries on failure, returns a structured error if all retries fail.
 * The model sees the result and decides what to do next — but your code
 * controls the retry logic, not the model.
 */
export async function executeToolSafely(toolCall, maxRetries = 2, toolsByName = null, verbose = false) {
  const registry = toolsByName || TOOLS_BY_NAME;
  const toolName = toolCall.name;
  const toolFn = registry[toolName];

  if (!toolFn) {
    return JSON.stringify({
      error: `Unknown tool: '${toolName}'`,
      available_tools: Object.keys(registry),
    });
  }

  let lastError = null;
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await toolFn.invoke(toolCall.args);
    } catch (e) {
      lastError = e.message || String(e);
      if (attempt <= maxRetries) {
        if (verbose) {
          console.log(`       ⚠️  attempt ${attempt} failed (${lastError}) — retrying…`);
        }
        await sleep(1000); // backoff before retry
      }
    }
  }

  return JSON.stringify({
    error: lastError,
    tool: toolName,
    status: "failed",
    attempts: maxRetries + 1,
    hint: "The tool is temporarily unavailable. Try a different approach.",
  });
}

/**
 * Full tool-calling loop: Request → Decide → Execute → Return → Answer.
 *
 * Bounded but multi-round: the model may chain tools; each result is fed
 * back until it produces plain text. If it never settles, an unbounded
 * final call forces text so the caller never gets an empty answer.
 */
export async function runToolLoop(userQuery, temperature = 0.0) {
  const llm = getLlm({ temperature });
  const llmWithTools = llm.bindTools(ALL_TOOLS);

  const messages = [
    new SystemMessage(
      "You are a helpful engineering assistant. You have access to tools " +
        "that can check service health, deployment history, and active incidents. " +
        "Use tools when you need live data. Answer directly for general questions."
    ),
    new HumanMessage(userQuery),
  ];

  for (let i = 0; i < MAX_TOOL_TURNS; i++) {
    const response = await llmWithTools.invoke(messages);
    messages.push(response);

    if (!response.tool_calls || response.tool_calls.length === 0) {
      return _asText(response);
    }

    for (const tc of response.tool_calls) {
      const result = await executeToolSafely(tc);
      messages.push(new ToolMessage({ content: result, tool_call_id: tc.id }));
    }
  }

  return _asText(await llm.invoke(messages));
}

/**
 * Same as runToolLoop, but returns a trace of every step — including
 * per-step token usage — for debugging, cost visibility, and demonstration.
 */
export async function runToolLoopWithTrace(userQuery, temperature = 0.0) {
  const llm = getLlm({ temperature });
  const llmWithTools = llm.bindTools(ALL_TOOLS);

  const trace = {
    query: userQuery,
    steps: [],
    tool_calls: [],
    tool_results: [],
    usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
  };

  const accrue = (u) => {
    trace.usage.input_tokens += u.input_tokens || 0;
    trace.usage.output_tokens += u.output_tokens || 0;
    trace.usage.total_tokens += u.total_tokens || 0;
  };

  const addAnswer = (text, message) => {
    const tokens = _usageOf(message);
    accrue(tokens);
    trace.answer = text;
    trace.steps.push({ type: "answer", content: text, tokens });
  };

  const messages = [
    new SystemMessage(
      "You are a helpful engineering assistant. You have access to tools " +
        "that can check service health, deployment history, and active incidents. " +
        "Use tools when you need live data. Answer directly for general questions."
    ),
    new HumanMessage(userQuery),
  ];

  for (let i = 0; i < MAX_TOOL_TURNS; i++) {
    const response = await llmWithTools.invoke(messages);
    messages.push(response);

    const tokens = _usageOf(response);
    accrue(tokens);
    trace.steps.push({
      type: "decide",
      content: String(response.content || "").slice(0, 200),
      tokens,
    });

    if (!response.tool_calls || response.tool_calls.length === 0) {
      addAnswer(_asText(response), response);
      return trace;
    }

    for (const tc of response.tool_calls) {
      trace.tool_calls.push({ name: tc.name, args: tc.args });
      const result = await executeToolSafely(tc);
      trace.tool_results.push({ tool: tc.name, result: result.slice(0, 200) });
      messages.push(new ToolMessage({ content: result, tool_call_id: tc.id }));
      trace.steps.push({ type: "execute", tool: tc.name, result: result.slice(0, 200) });
    }
  }

  const final = await llm.invoke(messages);
  addAnswer(_asText(final), final);
  return trace;
}
