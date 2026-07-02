/**
 * Week 4 — Tool definitions + function calling (Node.js)
 *
 * Tools are real functions the model can decide to call.
 * The model decides. Your code executes. This boundary is sacred.
 *
 * Imports: import { getLlm } from "./llm.js"
 */
import { z } from "zod";
import { tool } from "@langchain/core/tools";
import { HumanMessage, SystemMessage, ToolMessage } from "@langchain/core/messages";
import { getLlm } from "./llm.js";

// ═══════════════════════════════════════════════════════════════
// Tool definitions — mock implementations of live APIs
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

export const getBuildStatus = tool(
  async ({ service_name }) => {
    const data = BUILD_STATUSES[service_name];
    if (!data) {
      return JSON.stringify({
        status: "unknown",
        error: `No data for service '${service_name}'`,
      });
    }
    return JSON.stringify(data);
  },
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
  async ({ service_name, limit = 5 }) => {
    const serviceDeploys = DEPLOYS[service_name] || [];
    return JSON.stringify(serviceDeploys.slice(0, limit), null, 2);
  },
  {
    name: "get_recent_deploys",
    description:
      "Return the last N deployments for a given service. " +
      "Each deploy has: sha, author, timestamp, status. " +
      "Status is one of: 'success', 'failed', 'rolling_back'.",
    schema: z.object({
      service_name: z.string().describe("The name of the service to check"),
      limit: z.number().optional().default(5).describe("Max number of deploys to return"),
    }),
  }
);

export const getActiveIncidents = tool(
  async ({ service_name }) => {
    const serviceIncidents = INCIDENTS[service_name] || [];
    return JSON.stringify(serviceIncidents, null, 2);
  },
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

/**
 * Execute a tool call with error handling in the application layer.
 *
 * Retries on failure, returns a structured error if all retries fail.
 * The model sees the result and decides what to do next — but your code
 * controls the retry logic, not the model.
 */
export async function executeToolSafely(toolCall, maxRetries = 2) {
  const toolName = toolCall.name;
  const toolFn = TOOLS_BY_NAME[toolName];

  if (!toolFn) {
    return JSON.stringify({
      error: `Unknown tool: '${toolName}'`,
      available_tools: Object.keys(TOOLS_BY_NAME),
    });
  }

  let lastError = null;
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await toolFn.invoke(toolCall.args);
    } catch (e) {
      lastError = e.message;
      if (attempt <= maxRetries) {
        await new Promise((r) => setTimeout(r, 1000)); // backoff
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

  // Request → Decide
  const response = await llmWithTools.invoke(messages);
  messages.push(response);

  // Execute → Return
  if (response.tool_calls && response.tool_calls.length > 0) {
    for (const tc of response.tool_calls) {
      const result = await executeToolSafely(tc);
      messages.push(new ToolMessage({ content: result, tool_call_id: tc.id }));
    }

    // Answer
    const final = await llmWithTools.invoke(messages);
    return final.content.trim();
  }

  return response.content.trim();
}

/**
 * Same as runToolLoop, but returns a trace of every step.
 */
export async function runToolLoopWithTrace(userQuery, temperature = 0.0) {
  const llm = getLlm({ temperature });
  const llmWithTools = llm.bindTools(ALL_TOOLS);

  const trace = { query: userQuery, steps: [] };
  const messages = [
    new SystemMessage(
      "You are a helpful engineering assistant. You have access to tools " +
        "that can check service health, deployment history, and active incidents. " +
        "Use tools when you need live data. Answer directly for general questions."
    ),
    new HumanMessage(userQuery),
  ];

  const response = await llmWithTools.invoke(messages);
  messages.push(response);
  trace.steps.push({ type: "decide", content: (response.content || "").slice(0, 200) });

  if (response.tool_calls && response.tool_calls.length > 0) {
    trace.tool_calls = response.tool_calls.map((tc) => ({
      name: tc.name,
      args: tc.args,
    }));
    trace.tool_results = [];

    for (const tc of response.tool_calls) {
      const result = await executeToolSafely(tc);
      trace.tool_results.push({ tool: tc.name, result: result.slice(0, 200) });
      messages.push(new ToolMessage({ content: result, tool_call_id: tc.id }));
      trace.steps.push({ type: "execute", tool: tc.name, result: result.slice(0, 200) });
    }

    const final = await llmWithTools.invoke(messages);
    trace.answer = final.content.trim();
    trace.steps.push({ type: "answer", content: final.content.trim() });
  } else {
    trace.answer = response.content.trim();
    trace.steps.push({ type: "answer", content: response.content.trim() });
  }

  return trace;
}
