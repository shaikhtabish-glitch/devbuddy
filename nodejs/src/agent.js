/**
 * Week 6 — Agent Orchestrator: Multi-Step Workflows (Node.js)
 *
 * Composes retrieval (Week 3) and tool calling (Week 5) into an autonomous
 * pipeline using LangGraph. Retrieval imports src/rag.js directly. Tools go
 * through the MCP server (get_build_status, get_recent_deploys, etc.).
 *
 * Imports:
 *   import { getLlm } from "./llm.js"
 *   import { retrieve } from "./rag.js"  (context node)
 *   MCP SSE client for tool calls
 */
import { StateGraph, END } from "@langchain/langgraph";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { getLlm } from "./llm.js";

// ═══════════════════════════════════════════════════════════════
// MCP tool calls — SSE client to long-lived server
// ═══════════════════════════════════════════════════════════════

const MCP_URL = "http://127.0.0.1:3001/sse";

async function callMcpTool(toolName, args) {
  /** Call a tool on the MCP server over SSE. */
  try {
    // Use JSON-RPC over HTTP to the SSE endpoint
    const response = await fetch(`${MCP_URL.replace("/sse", "")}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/call",
        params: { name: toolName, arguments: args },
        id: Date.now(),
      }),
    });
    const data = await response.json();
    if (data.error) {
      return JSON.stringify({ error: data.error.message, tool: toolName });
    }
    // Extract text content from the result
    const content = data.result?.content || [];
    return content.map((c) => c.text).join("\n") || JSON.stringify(data.result);
  } catch (e) {
    return JSON.stringify({ error: e.message, tool: toolName, status: "failed" });
  }
}

// ═══════════════════════════════════════════════════════════════
// Agent State
// ═══════════════════════════════════════════════════════════════

/**
 * @typedef {Object} AgentState
 * @property {string} query
 * @property {string} service_name
 * @property {string} context
 * @property {string} build_status
 * @property {string} deploys
 * @property {string} incidents
 * @property {string} report
 * @property {number} steps
 * @property {number} cost
 */

function initState(query) {
  return {
    query,
    service_name: "",
    context: "",
    build_status: "",
    deploys: "",
    incidents: "",
    report: "",
    steps: 0,
    cost: 0.0,
  };
}

function estimateCost(response) {
  const usage = response.usage_metadata || {};
  const inp = usage.input_tokens || 0;
  const out = usage.output_tokens || 0;
  return (inp * 0.15 + out * 0.60) / 1_000_000;
}

// ═══════════════════════════════════════════════════════════════
// Nodes — each is one step in the workflow
// ═══════════════════════════════════════════════════════════════

async function extractService(state) {
  if (state.service_name) return state;

  const llm = getLlm({ temperature: 0 });
  const response = await llm.invoke([
    new SystemMessage(
      "Extract the service name from the user's query. " +
        "Respond with EXACTLY ONE WORD: the service name. " +
        "Known services: auth-service, payment-api, inventory-service. " +
        "If no service is mentioned, respond with 'payment-api' as default."
    ),
    new HumanMessage(state.query),
  ]);
  state.service_name = response.content.trim().toLowerCase();
  state.steps++;
  state.cost += estimateCost(response);
  return state;
}

async function retrieveContext(state) {
  try {
    const { retrieve: ragRetrieve } = await import("./rag.js");
    const chunks = await ragRetrieve(state.query, 3);
    state.context = chunks.length > 0
      ? chunks.join("\n\n---\n\n")
      : "(no relevant documents found)";
  } catch (e) {
    state.context = `(retrieval error: ${e.message})`;
  }
  state.steps++;
  return state;
}

async function checkBuild(state) {
  const svc = state.service_name || "payment-api";
  const result = await callMcpTool("get_build_status", { service_name: svc });
  state.build_status = result;
  state.steps++;
  return state;
}

async function checkDeploys(state) {
  const svc = state.service_name || "payment-api";
  const result = await callMcpTool("get_recent_deploys", {
    service_name: svc,
    limit: 3,
  });
  state.deploys = result;
  state.steps++;
  return state;
}

async function checkIncidents(state) {
  const svc = state.service_name || "payment-api";
  const result = await callMcpTool("get_active_incidents", {
    service_name: svc,
  });
  state.incidents = result;
  state.steps++;
  return state;
}

async function generateReport(state) {
  const llm = getLlm({ temperature: 0 });

  const sections = ["Summary — one sentence answering the user's query"];
  const dataParts = [`Query: ${state.query}`];

  if (state.context) {
    sections.push("Relevant Documentation");
    dataParts.push(`Relevant docs:\n${state.context}`);
  }
  if (state.build_status) {
    sections.push("Build Status");
    dataParts.push(`Build status: ${state.build_status}`);
  }
  if (state.deploys) {
    sections.push("Recent Deployments");
    dataParts.push(`Recent deployments: ${state.deploys}`);
  }
  if (state.incidents) {
    sections.push("Active Incidents");
    dataParts.push(`Active incidents: ${state.incidents}`);
  }

  const response = await llm.invoke([
    new SystemMessage(
      "You are a site reliability engineer. Answer the user's query " +
        "using ONLY the data provided. Do not invent information. " +
        "Do not mention sections where no data was collected.\n\n" +
        `Include these sections:\n${sections.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
    ),
    new HumanMessage(dataParts.join("\n\n")),
  ]);

  state.report = response.content;
  state.steps++;
  state.cost += estimateCost(response);
  return state;
}

// ═══════════════════════════════════════════════════════════════
// Router — model decides the next step dynamically
// ═══════════════════════════════════════════════════════════════

async function router(state) {
  const llm = getLlm({ temperature: 0 });
  const response = await llm.invoke([
    new SystemMessage(
      "You are a workflow router. Based on the user's query and what data " +
        "has already been collected, decide the NEXT step to run. " +
        "Respond with EXACTLY ONE WORD from this list:\n\n" +
        "- retrieve   (if the query asks about documentation or context)\n" +
        "- check_build   (ONLY if the query asks about health, status, healthy, or readiness)\n" +
        "- check_deploys (ONLY if the query asks about deployments, releases, deployed)\n" +
        "- check_incidents (ONLY if the query asks about incidents, outages, issues, or alerts)\n" +
        "- report    (if all NEEDED data has been collected for this specific query)\n" +
        "- done      (if the task is complete or cannot proceed)\n\n" +
        "IMPORTANT: Only run steps the query explicitly asks for. " +
        "Do NOT cascade. 'healthy?' does NOT mean 'also check incidents'."
    ),
    new HumanMessage(
      `QUERY: ${state.query}\n\n` +
        `CURRENT STATE:\n` +
        `- Steps completed: ${state.steps}\n` +
        `- Context retrieved: ${state.context ? "YES" : "NO"}\n` +
        `- Build status checked: ${state.build_status ? "YES" : "NO"}\n` +
        `- Deploys checked: ${state.deploys ? "YES" : "NO"}\n` +
        `- Incidents checked: ${state.incidents ? "YES" : "NO"}\n\n` +
        `NEVER return a step that already has data (YES above). ` +
        `If all needed data is YES, return 'report'.\n\n` +
        `Next step:`
    ),
  ]);

  const decision = response.content.trim().toLowerCase();
  state.cost += estimateCost(response);
  return decision;
}

// ═══════════════════════════════════════════════════════════════
// Guard — stop if limits exceeded
// ═══════════════════════════════════════════════════════════════

const MAX_STEPS = 10;
const MAX_COST = 2.0;

async function guard(state) {
  if (state.steps >= MAX_STEPS || state.cost >= MAX_COST) {
    return "done";
  }
  return await router(state);
}

// ═══════════════════════════════════════════════════════════════
// Graph builders — fixed chain and dynamic routing
// ═══════════════════════════════════════════════════════════════

export function buildFixedChain() {
  const graph = new StateGraph({ channels: initState("") });
  graph.addNode("extract_service", extractService);
  graph.addNode("retrieve", retrieveContext);
  graph.addNode("check_build", checkBuild);
  graph.addNode("report", generateReport);
  graph.addEdge("__start__", "extract_service");
  graph.addEdge("extract_service", "retrieve");
  graph.addEdge("retrieve", "check_build");
  graph.addEdge("check_build", "report");
  graph.addEdge("report", END);
  return graph.compile();
}

export function buildDynamicAgent() {
  const graph = new StateGraph({ channels: initState("") });
  graph.addNode("extract_service", extractService);
  graph.addNode("retrieve", retrieveContext);
  graph.addNode("check_build", checkBuild);
  graph.addNode("check_deploys", checkDeploys);
  graph.addNode("check_incidents", checkIncidents);
  graph.addNode("report", generateReport);

  graph.addEdge("__start__", "extract_service");
  graph.addEdge("extract_service", "retrieve");

  const edges = {
    retrieve: "retrieve",
    check_build: "check_build",
    check_deploys: "check_deploys",
    check_incidents: "check_incidents",
    report: "report",
    done: END,
  };

  for (const node of ["retrieve", "check_build", "check_deploys", "check_incidents"]) {
    graph.addConditionalEdges(node, guard, edges);
  }

  return graph.compile();
}

// ═══════════════════════════════════════════════════════════════
// Convenience functions
// ═══════════════════════════════════════════════════════════════

export async function runFixedChain(query) {
  const agent = buildFixedChain();
  return await agent.invoke(initState(query));
}

export async function runDynamicAgent(query) {
  const agent = buildDynamicAgent();
  return await agent.invoke(initState(query));
}
