/**
 * Week 4 — Tool definitions + function calling (Node.js)
 *
 * Tools are real functions the model can decide to call.
 * The model decides. Your code executes. This boundary is sacred.
 *
 * Design (single source of truth):
 *   • Raw functions  — buildStatus / recentDeploys / activeIncidents —
 *     own the data. Demos wrap these (e.g. to inject failures) without
 *     re-defining or duplicating anything.
 *   • tool wrappers  — getBuildStatus / getRecentDeploys / getActiveIncidents —
 *     own the schema the model sees. Their description is what teaches
 *     the model to route.
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
  "auth-service": {
    status: "healthy",
    last_deploy: "2026-06-28T08:15:00Z",
  },
  "payment-api": {
    status: "degraded",
    last_deploy: "2026-06-28T06:45:00Z",
    failing_since: "2026-06-28T07:30:00Z",
  },
  "inventory-service": {
    status: "unknown",
    last_deploy: "2026-06-20T11:00:00Z",
  },
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

const ACTIVE_INCIDENTS = {
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

/** Return the current build/health status of a service as JSON. */
export function buildStatus(serviceName) {
  const data = BUILD_STATUSES[serviceName];
  if (!data) {
    return JSON.stringify({
      status: "unknown",
      error: `No data for service '${serviceName}'`,
    });
  }
  return JSON.stringify(data);
}

/** Return the last N deployments of a service as JSON. */
export function recentDeploys(serviceName, limit = 5) {
  const serviceDeploys = DEPLOYS[serviceName] || [];
  return JSON.stringify(serviceDeploys.slice(0, limit), null, 2);
}

/** Return any active (unresolved) incidents of a service as JSON. */
export function activeIncidents(serviceName) {
  const serviceIncidents = ACTIVE_INCIDENTS[serviceName] || [];
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
export const TOOLS_BY_NAME = Object.fromEntries(
  ALL_TOOLS.map((t) => [t.name, t])
);

// Upper bound on tool-calling rounds. The model may chain tools (status →
// deploys → incidents); if it never settles on a text answer we force one.
// A model that never stops calling tools is a cost event, not a feature.
export const MAX_TOOL_TURNS = 6;

/** Error type used by flaky() to simulate transient infrastructure failures. */
export class ConnectionError extends Error {
  constructor(message) {
    super(message);
    this.name = "ConnectionError";
  }
}

/**
 * Deterministic failure injection for demos/tests.
 *
 * Wraps a raw function (e.g. buildStatus) so the first `failFirstN` calls
 * raise `ErrorType` and later calls succeed. Each wrapper owns its own
 * counter, so scenarios are self-contained — no shared global state, no
 * reliance on call order across scenarios.
 *
 * @param {Function} fn - The function to wrap (a raw data function).
 * @param {number} [failFirstN=0] - Number of initial calls that fail (0 = never).
 * @param {Function} [ErrorType=ConnectionError] - Error class to throw while failing.
 * @returns {Function} Wrapped function with the same signature as fn.
 */
export function flaky(fn, failFirstN = 0, ErrorType = ConnectionError) {
  let made = 0;
  const wrapped = (...args) => {
    made += 1;
    if (made <= failFirstN) {
      throw new ErrorType(`Simulated failure ${made}/${failFirstN}`);
    }
    return fn(...args);
  };
  Object.defineProperty(wrapped, "name", {
    value: `flaky_${fn.name || "fn"}`,
    configurable: true,
  });
  return wrapped;
}

/** Extract plain text from an AI message (handles str or content blocks). */
export function _asText(message) {
  const content = message.content;
  if (typeof content === "string") return content.trim();
  if (Array.isArray(content)) {
    return content
      .map((block) => (typeof block === "string" ? block : block?.text || ""))
      .join("")
      .trim();
  }
  return String(content ?? "").trim();
}

/** Best-effort token usage from a LangChain message's usage_metadata. */
export function _usageOf(message) {
  const md = message.usage_metadata || {};
  return {
    input_tokens: md.input_tokens || 0,
    output_tokens: md.output_tokens || 0,
    total_tokens: md.total_tokens || 0,
  };
}

/**
 * Execute a tool call with error handling in the application layer.
 *
 * Retries on failure, returns a structured error if all retries fail.
 * The model sees the result and decides what to do next — but your code
 * controls the retry logic, not the model.
 *
 * @param {Object} toolCall - A tool call object from the model's response.
 * @param {number} [maxRetries=2] - Number of retry attempts.
 * @param {Object} [options]
 * @param {Object} [options.toolsByName] - Registry to resolve tool names from.
 *   Defaults to the module-level TOOLS_BY_NAME. Demos pass a registry that
 *   maps a tool to a flaky wrapper to exercise retries.
 * @param {boolean} [options.verbose=false] - Print each failed attempt.
 * @param {number} [options.retryDelayMs=1000] - Backoff before each retry.
 * @returns {Promise<string>} Tool result as JSON, or a structured error string.
 */
export async function executeToolSafely(toolCall, maxRetries = 2, options = {}) {
  const {
    toolsByName = TOOLS_BY_NAME,
    verbose = false,
    retryDelayMs = 1000,
  } = options;

  const toolName = toolCall.name;
  const toolFn = toolsByName[toolName];

  if (!toolFn) {
    return JSON.stringify({
      error: `Unknown tool: '${toolName}'`,
      available_tools: Object.keys(toolsByName),
    });
  }

  let lastError = null;
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await toolFn.invoke(toolCall.args);
    } catch (e) {
      lastError = e.message;
      if (attempt <= maxRetries) {
        if (verbose) {
          console.log(`       ⚠️  attempt ${attempt} failed (${e.message}) — retrying…`);
        }
        if (retryDelayMs > 0) {
          await new Promise((r) => setTimeout(r, retryDelayMs));
        }
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

const AGENT_SYSTEM_PROMPT =
  "You are a helpful engineering assistant. You have access to tools " +
  "that can check service health, deployment history, and active incidents. " +
  "Use tools when you need live data. Answer directly for general questions.";

/**
 * Full tool-calling loop: Request → Decide → Execute → Return → Answer.
 *
 * The loop is bounded but multi-round: the model may chain as many tool
 * calls as it needs (e.g. status, then deploys, then incidents). Each tool
 * result is injected back into the conversation until the model produces a
 * plain-text answer. If it never settles, an unbounded final call forces
 * text so the caller always gets an answer, never an empty string.
 *
 * @param {string} userQuery - The user's question.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @returns {Promise<string>} The model's final answer.
 */
export async function runToolLoop(userQuery, temperature = 0.0) {
  const llm = getLlm({ temperature });
  const llmWithTools = llm.bindTools(ALL_TOOLS);

  const messages = [
    new SystemMessage(AGENT_SYSTEM_PROMPT),
    new HumanMessage(userQuery),
  ];

  for (let turn = 0; turn < MAX_TOOL_TURNS; turn++) {
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

  // The model kept calling tools — drop the tools and force a text answer.
  const final = await llm.invoke(messages);
  return _asText(final);
}

/**
 * Same as runToolLoop, but returns a trace of every step — including
 * per-step token usage — for debugging, cost visibility, and demonstration.
 *
 * @param {string} userQuery - The user's question.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @returns {Promise<Object>} Trace with answer, tool_calls, tool_results,
 *   steps, and aggregated usage.
 */
export async function runToolLoopWithTrace(userQuery, temperature = 0.0) {
  const llm = getLlm({ temperature });
  const llmWithTools = llm.bindTools(ALL_TOOLS);

  const trace = {
    query: userQuery,
    steps: [],
    tool_calls: [],
    tool_results: [],
    usage: {},
  };
  const usageTotals = { input_tokens: 0, output_tokens: 0, total_tokens: 0 };
  const accrue = (usage) => {
    for (const key of Object.keys(usageTotals)) {
      usageTotals[key] += usage[key] || 0;
    }
  };

  const messages = [
    new SystemMessage(AGENT_SYSTEM_PROMPT),
    new HumanMessage(userQuery),
  ];

  for (let turn = 0; turn < MAX_TOOL_TURNS; turn++) {
    const response = await llmWithTools.invoke(messages);
    messages.push(response);

    const usage = _usageOf(response);
    accrue(usage);
    trace.steps.push({
      type: "decide",
      content: String(response.content ?? "").slice(0, 200),
      tokens: usage,
    });

    if (!response.tool_calls || response.tool_calls.length === 0) {
      trace.answer = _asText(response);
      trace.steps.push({ type: "answer", content: trace.answer, tokens: usage });
      trace.usage = usageTotals;
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

  // The model kept calling tools — drop the tools and force a text answer.
  const final = await llm.invoke(messages);
  const usage = _usageOf(final);
  accrue(usage);
  trace.answer = _asText(final);
  trace.steps.push({ type: "answer", content: trace.answer, tokens: usage });
  trace.usage = usageTotals;
  return trace;
}
