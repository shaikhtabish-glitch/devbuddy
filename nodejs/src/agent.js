/**
 * Week 6 — Agent Orchestrator: Multi-Step Workflows (Node.js)
 *
 * The Node sibling of the Python reference. Same teaching architecture:
 *
 *   from ./llm.js         getLlm                (Week 1)
 *   from ./schemas.js     AgentAnswerSchema     (Week 2 — validators on output)
 *   from ./rag.js         retrieve              (Week 3 — direct, local)
 *   callMcpTool(...)                            (Week 5 server over SSE)
 *
 *   NODE_REGISTRY → router catalog, route map, guard requirements,
 *   refusal message — one source of truth, four surfaces.
 *   Three guards: budget (operational), plan (structural), validate (business).
 *
 * Deliberate scope differences vs Python (docs → Scope: languages):
 *   - data fields stay strings (no BuildStatus/DeployRecord contracts)
 *   - no TOOL_BACKEND seam — retrieval is local, tools are MCP
 * Everything else — audit trail, structured report, C2/C3 graphs — matches.
 */
import { StateGraph, END } from "@langchain/langgraph";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { getLlm } from "./llm.js";
import { AgentAnswerSchema } from "./schemas.js";
import { retrieve } from "./rag.js";

// ═══════════════════════════════════════════════════════════════
// MCP tool calls — SSE client to long-lived server (port 3001)
// ═══════════════════════════════════════════════════════════════

const MCP_URL = "http://127.0.0.1:3001/sse";
let _mcpClient = null;

async function getMcpClient() {
  if (!_mcpClient) {
    const transport = new SSEClientTransport(new URL(MCP_URL));
    const client = new Client(
      { name: "devbuddy-agent-client", version: "0.1.0" },
      { capabilities: {} }
    );
    await client.connect(transport);
    _mcpClient = client;
  }
  return _mcpClient;
}

async function callMcpTool(toolName, args) {
  /** Call a tool on the MCP server over SSE. Returns raw text or throws. */
  try {
    const client = await getMcpClient();
    const result = await client.callTool({
      name: toolName,
      arguments: args,
    });
    return result.content[0].text;
  } catch (e) {
    throw new Error(`${toolName}: ${e.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════
// Agent State — carried across all steps
// ═══════════════════════════════════════════════════════════════

/**
 * @typedef {Object} AgentState
 * @property {string} query
 * @property {string} service_name
 * @property {string} context            "" = not retrieved yet
 * @property {string} build_status       "" = not checked yet (JSON when set)
 * @property {string} deploys            "" = not checked yet (JSON array when set)
 * @property {string} incidents          "" = not checked yet (JSON array when set)
 * @property {AgentAnswer|null} report   null = not generated yet
 * @property {string} next_step          planner's accepted decision
 * @property {number} steps
 * @property {number} cost
 * @property {string} error              "" = no failure so far
 * @property {Array<Object>} messages    audit trail — recorded, never reconstructed
 */
export function initState(query) {
  return {
    query,
    service_name: "",
    context: "",
    build_status: "",
    deploys: "",
    incidents: "",
    report: null,
    next_step: "",
    steps: 0,
    cost: 0.0,
    error: "",
    messages: [],
  };
}

/**
 * Append one event to the audit trail. Every node records itself, and
 * carries the COST DELTA since the previous event — per-step cost is
 * traceable, not just the run total.
 */
export function record(state, step, detail = {}) {
  const prevTotal = state.messages.reduce((s, m) => s + (m.cost || 0), 0);
  state.messages.push({
    step,
    ...detail,
    cost: Math.round((state.cost - prevTotal) * 1e6) / 1e6,
  });
}

function estimateCost(response) {
  const usage = response.usage_metadata || response.usageMetadata || {};
  const inp = usage.input_tokens || 0;
  const out = usage.output_tokens || 0;
  return (inp * 0.15 + out * 0.60) / 1_000_000;
}

function usageCapture() {
  /** Capture token usage from a structured-output invoke (result is a
   *  model, not a message — callbacks see the intermediate message). */
  const usage = { input_tokens: 0, output_tokens: 0, total_tokens: 0 };
  return {
    usage,
    callbacks: [
      {
        handleLLMEnd(output) {
          try {
            const msg = output.generations?.[0]?.[0]?.message;
            const md = msg?.usage_metadata || msg?.usageMetadata;
            if (md) {
              for (const key of Object.keys(usage)) {
                usage[key] = (usage[key] || 0) + (md[key] || 0);
              }
            }
          } catch {
            /* usage is best-effort */
          }
        },
      },
    ],
  };
}

function usageCost(usage) {
  return (
    ((usage.input_tokens || 0) * 0.15 + (usage.output_tokens || 0) * 0.60) /
    1_000_000
  );
}

// ═══════════════════════════════════════════════════════════════
// Report rendering — shared by every demo
// ═══════════════════════════════════════════════════════════════

export function formatReport(report) {
  if (!report) return "(no report generated)";
  const lines = [report.answer];
  if (report.verdict) {
    const v = report.verdict;
    lines.push("");
    lines.push(`  ready      : ${v.ready}  (confidence: ${v.confidence})`);
    for (const b of v.blockers) lines.push(`  blocker    : ${b}`);
    for (const n of v.recommended_next_steps)
      lines.push(`  next step  : ${n}`);
  }
  if (report.evidence?.length) {
    lines.push("");
    for (const e of report.evidence) {
      const score =
        e.relevance_score !== null && e.relevance_score !== undefined
          ? ` (${e.relevance_score})`
          : "";
      lines.push(`  evidence[${e.source}]${score}: ${e.content.slice(0, 100)}`);
    }
  }
  return lines.join("\n");
}

// ═══════════════════════════════════════════════════════════════
// Nodes — each is one step in the workflow
// ═══════════════════════════════════════════════════════════════

function isFailure(raw) {
  try {
    const data = JSON.parse(raw);
    return (
      data.status === "failed" ||
      (data.error !== undefined && data.status === undefined)
    );
  } catch {
    return true; // unparseable = failure
  }
}

function toolFailure(state, step, message) {
  state.error = `${step}: ${message}`;
  record(state, step, { status: "failed", error: message });
}

export async function extractService(state) {
  if (state.service_name) {
    record(state, "extract_service", {
      service: state.service_name,
      cached: true,
    });
    return state;
  }

  const llm = getLlm({ temperature: 0 });
  let response = await llm.invoke([
    new SystemMessage(
      "Extract the service name from the user's query. " +
        "Respond with EXACTLY ONE WORD: the service name. " +
        "Known services: auth-service, payment-api, inventory-service. " +
        "If no service is mentioned, respond with 'payment-api' as default."
    ),
    new HumanMessage(state.query),
  ]);
  let name = response.content.trim().toLowerCase();
  if (!name) {
    // empty completion (provider quirk at temp=0) — retry once
    response = await llm.invoke([
      new HumanMessage(`${state.query}\n\nService name:`),
    ]);
    name = response.content.trim().toLowerCase() || "payment-api";
  }
  state.service_name = name;
  state.steps++;
  state.cost += estimateCost(response);
  record(state, "extract_service", { service: name });
  return state;
}

export async function retrieveContext(state) {
  try {
    const chunks = await retrieve(state.query, 3);
    state.context =
      chunks.length > 0 ? chunks.join("\n\n---\n\n") : "(no relevant documents found)";
    record(state, "retrieve_context", { chunks: chunks.length });
  } catch (e) {
    // Retrieval failed → context stays empty AND the failure is visible.
    state.context = "";
    toolFailure(state, "retrieve_context", e.message);
  }
  state.steps++;
  return state;
}

export async function checkBuild(state) {
  try {
    const raw = await callMcpTool("get_build_status", {
      service_name: state.service_name || "payment-api",
    });
    if (isFailure(raw)) throw new Error(raw.slice(0, 160));
    const data = JSON.parse(raw);
    if (!data.status) throw new Error(`no status field: ${raw.slice(0, 120)}`);
    state.build_status = raw;
    record(state, "check_build", { status: data.status });
  } catch (e) {
    toolFailure(state, "check_build", e.message);
  }
  state.steps++;
  return state;
}

export async function checkDeploys(state) {
  try {
    const raw = await callMcpTool("get_recent_deploys", {
      service_name: state.service_name || "payment-api",
      limit: 3,
    });
    if (isFailure(raw)) throw new Error(raw.slice(0, 160));
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) throw new Error(`expected an array: ${raw.slice(0, 120)}`);
    state.deploys = raw;
    record(state, "check_deploys", { count: data.length });
  } catch (e) {
    toolFailure(state, "check_deploys", e.message);
  }
  state.steps++;
  return state;
}

export async function checkIncidents(state) {
  try {
    const raw = await callMcpTool("get_active_incidents", {
      service_name: state.service_name || "payment-api",
    });
    if (isFailure(raw)) throw new Error(raw.slice(0, 160));
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) throw new Error(`expected an array: ${raw.slice(0, 120)}`);
    state.incidents = raw;
    record(state, "check_incidents", { count: data.length });
  } catch (e) {
    toolFailure(state, "check_incidents", e.message);
  }
  state.steps++;
  return state;
}

function dataSection(label, value) {
  /** None-ish ("") means NOT CHECKED — and it says so, in caps. */
  if (!value) return `${label}: NOT CHECKED (step was skipped or failed)`;
  return `${label}:\n${value}`;
}

function naiveDataSection(label, value) {
  /** The VULNERABLE rendering: missing state becomes '{}'. */
  if (!value) return `${label}: {}`;
  return `${label}:\n${value}`;
}

const REPORT_RULES =
  "You are a site reliability engineer. Answer the user's query using ONLY " +
  "the data provided below. Rules:\n" +
  "- If a section says NOT CHECKED, say so plainly — never invent data for it.\n" +
  "- If build status is 'degraded' or 'down', verdict.ready must be False " +
  "and blockers must say why.\n" +
  "- Set a verdict (ready/blockers/next steps) for readiness or health queries; " +
  "leave verdict null for docs or general questions.\n" +
  "- verdict.confidence must be 'low' unless evidence supports it.\n" +
  "- Every claim must cite its source in evidence: 'rag' for documentation, " +
  "'tool' for build/deploy/incident data, 'user' for the query itself.\n" +
  "- ready=true with blockers, or ready=false with no blockers, will be " +
  "REJECTED by the contract validator — be consistent.";

function withTimeout(promise, ms, label) {
  /** Providers occasionally stall a request indefinitely — a report call
   *  must never hang the graph. Reject after `ms`; the timer is always
   *  cleared so the process can exit. */
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`${label} timed out after ${ms}ms`)),
      ms
    );
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function invokeStructured(system, sections, state, step) {
  const llm = getLlm({ temperature: 0 });
  const structured = llm.withStructuredOutput(AgentAnswerSchema, {
    name: "AgentAnswer",
  });
  const capture = usageCapture();
  // Provider stalls come in bursts (>40s observed) — a fresh request
  // after a short backoff usually succeeds. 15s × 3 attempts caps total
  // wait at ~50s including backoff.
  const INVOKE_TIMEOUT_MS = 15_000;
  const MAX_ATTEMPTS = 3;

  let lastError = null;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    if (attempt > 1) {
      await new Promise((r) => setTimeout(r, 1500)); // burst backoff
    }
    // Perturb each retry — identical requests at temp=0 can replay the
    // same stuck/empty completion (same quirk the Python loops guard
    // against with _final_answer's nudge).
    const human = new HumanMessage(
      attempt === 1
        ? sections
        : `${sections}\n\n(Attempt ${attempt} — respond now, in an AgentAnswer.)`
    );
    try {
      const answer = await withTimeout(
        structured.invoke(
          [new SystemMessage(system), human],
          { callbacks: capture.callbacks }
        ),
        INVOKE_TIMEOUT_MS,
        `${step} (attempt ${attempt})`
      );
      state.cost += usageCost(capture.usage);
      state.report = answer;
      record(state, step, {
        ready: answer.verdict ? answer.verdict.ready : null,
        evidence: answer.evidence.length,
      });
      return;
    } catch (e) {
      lastError = e;
    }
  }

  // Last resort: function-calling stalls on this provider in bursts, but
  // plain invokes never do. Ask for raw JSON and validate it through the
  // SAME contract — the seam changes, the contract does not.
  try {
    const plainLlm = getLlm({ temperature: 0 });
    const response = await withTimeout(
      plainLlm.invoke([
        new SystemMessage(
          `${system}\n\nReturn ONLY a valid JSON object, no markdown fences, ` +
            `shaped like: {"answer": string, "verdict": null | ` +
            `{"ready": boolean, "confidence": "low|medium|high", ` +
            `"blockers": string[], "recommended_next_steps": string[]}, ` +
            `"evidence": [{"source": "rag|tool|user", "content": string, ` +
            `"relevance_score": number|null}]}`
        ),
        new HumanMessage(sections),
      ]),
      INVOKE_TIMEOUT_MS,
      `${step} (plain fallback)`
    );
    state.cost += estimateCost(response);
    let text = String(response.content || "").trim();
    if (text.startsWith("```")) {
      text = text.replace(/^```(?:json)?\n?/, "").replace(/```\s*$/, "").trim();
    }
    const answer = AgentAnswerSchema.parse(JSON.parse(text)); // contract enforced
    state.report = answer;
    record(state, step, {
      ready: answer.verdict ? answer.verdict.ready : null,
      evidence: answer.evidence.length,
      via: "plain-json-fallback",
    });
    return;
  } catch (e) {
    lastError = lastError || e;
  }
  // Contract violation at the boundary: surfaced, never hidden.
  state.cost += usageCost(capture.usage);
  state.error = `${step}: ${lastError.message}`;
  state.report = {
    answer:
      "(report generation failed — the model's output did not satisfy " +
      "the AgentAnswer contract. See error.)",
    verdict: null,
    evidence: [],
  };
  record(state, step, { status: "failed", error: lastError.message });
}

export async function generateReport(state) {
  const sections = [
    `Query: ${state.query}`,
    dataSection("Relevant documentation", state.context),
    dataSection("Build status", state.build_status),
    dataSection("Recent deployments", state.deploys),
    dataSection("Active incidents", state.incidents),
  ].join("\n\n");

  await invokeStructured(
    REPORT_RULES,
    `Query + data:\n\n${sections}`,
    state,
    "generate_report"
  );
  state.steps++;
  return state;
}

// ── C2 teaching node — DELIBERATELY UNDEFENDED (demo-04 only) ──

export async function generateReportNaive(state) {
  /** Renders missing state as '{}' and gives the model NO ground rules —
   *  the pattern that makes agents hallucinate missing steps. */
  const sections = [
    `Query: ${state.query}`,
    naiveDataSection("Relevant documentation", state.context),
    naiveDataSection("Build status", state.build_status),
    naiveDataSection("Recent deployments", state.deploys),
    naiveDataSection("Active incidents", state.incidents),
  ].join("\n\n");

  const system =
    "You are a site reliability engineer. Generate a complete release " +
    "readiness report based on the following data. Be specific and " +
    "decisive: state the build health, the deployment state, and whether " +
    "the service is ready to ship. Return an AgentAnswer.";

  await invokeStructured(
    system,
    `Query + data:\n\n${sections}`,
    state,
    "generate_report_naive"
  );
  state.steps++;
  return state;
}

// ═══════════════════════════════════════════════════════════════
// Registry — the single source of truth for what the agent can do
// ═══════════════════════════════════════════════════════════════

export const NODE_REGISTRY = {
  retrieve: {
    fn: retrieveContext,
    node_id: "retrieve_context",
    data_field: "context",
    desc: "Search internal documentation for the query (no service needed)",
  },
  check_build: {
    fn: checkBuild,
    node_id: "check_build",
    data_field: "build_status",
    desc: "Get CI/CD build/health status for the service",
  },
  check_deploys: {
    fn: checkDeploys,
    node_id: "check_deploys",
    data_field: "deploys",
    desc: "Get recent deployment history for the service",
  },
  check_incidents: {
    fn: checkIncidents,
    node_id: "check_incidents",
    data_field: "incidents",
    desc: "Get active (unresolved) incidents for the service",
  },
};

const FIELD_TO_STEP = Object.fromEntries(
  Object.entries(NODE_REGISTRY).map(([name, spec]) => [spec.data_field, name])
);

/** Query category → state fields that MUST be present before a report. */
export const REQUIREMENTS = {
  full: ["build_status", "deploys", "incidents"],
  readiness: ["build_status", "deploys"],
  health: ["build_status"],
  deploys: ["deploys"],
  incidents: ["incidents"],
  docs: ["context"],
  general: [],
  action: [], // imperative — refused before validate ever runs
};

/** Imperative operational actions — refused deterministically, before
 *  any LLM call. An agent with no deploy tool must not depend on a
 *  lucky prompt to refuse a deploy. */
export const IMPERATIVE_ACTIONS =
  /^\s*(deploy|roll\s?back|rollback|restart|scale|delete|kill|shutdown|wipe)\b/;

/** Deterministic query categories — code, not prompt. Returns ALL matched
 *  categories joined with '+' (multi-intent queries get the UNION of steps
 *  and requirements). */
export function classifyQuery(query) {
  const q = query.toLowerCase();
  if (IMPERATIVE_ACTIONS.test(q)) return "action";
  if (/\b(full|everything|all checks|end-to-end)\b/.test(q)) return "full";

  const cats = [];
  if (/\b(ready|readiness|release|assessment|ship)\b/.test(q)) cats.push("readiness");
  if (/(incident|outage|alert)/.test(q)) cats.push("incidents");
  if (/(deployed|deployment|\bsha\b|version)/.test(q)) cats.push("deploys");
  if (/(healthy|health|status|\bbuild\b)/.test(q)) cats.push("health");
  // NOTE: no bare "api" — service names like "payment-api" would match
  // every query and silently force the docs category.
  if (/(doc|spec|endpoint|sla|\bhow\b|what is|why|describe|explain)/.test(q))
    cats.push("docs");
  return cats.length ? cats.join("+") : "general";
}

function routerCatalog() {
  const lines = Object.entries(NODE_REGISTRY).map(
    ([name, spec]) => `- ${name}: ${spec.desc}`
  );
  lines.push("- report: every field NEEDED for this query has been collected");
  lines.push("- done: the task is complete or cannot proceed");
  return lines.join("\n");
}

/** The graph's route map — GENERATED from the registry too. 'done' from
 *  the planner = "wrap up" → the GUARD decides. Only 'stop' ends the run. */
export const PLAN_ROUTE_MAP = {
  ...Object.fromEntries(Object.keys(NODE_REGISTRY).map((k) => [k, k])),
  report: "validate",
  done: "validate",
  validate: "validate",
  refuse: "refuse",
  stop: END,
};

// ═══════════════════════════════════════════════════════════════
// Router — model PROPOSES the next step (registry decides)
// ═══════════════════════════════════════════════════════════════

async function router(state, correction = null) {
  const llm = getLlm({ temperature: 0 });
  let system =
    "You are a workflow router. Based on the user's query and what data " +
    "has already been collected, propose the NEXT step. Respond with " +
    "EXACTLY ONE WORD from this list:\n\n" +
    `${routerCatalog()}\n\n` +
    "Rules:\n" +
    "- Only run steps the query explicitly asks for. Do NOT cascade: " +
    "'healthy?' does not mean 'also check incidents'.\n" +
    "- NEVER propose a step whose data is already YES below.\n" +
    "- Docs/API/spec/SLA questions → retrieve only. Health/status → check_build " +
    "only. Deployments → check_deploys only. Incidents → check_incidents only.\n" +
    "- Propose 'report' as soon as everything the query needs is YES.\n" +
    "- If instead the query asks you to PERFORM an operational action " +
    "(deploy, rollback, restart, scale, delete), respond with that single " +
    "action word — it will be checked against the registry.\n";
  if (correction) system += `CORRECTION: ${correction}\n`;

  let response = await llm.invoke([
    new SystemMessage(system),
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

  let decision = response.content.trim().toLowerCase();
  if (!decision) {
    // empty completion — retry once before trusting an empty proposal
    response = await llm.invoke([
      new HumanMessage(
        `QUERY: ${state.query}\n\nAvailable steps:\n${routerCatalog()}\n\nNext step (one word):`
      ),
    ]);
    decision = response.content.trim().toLowerCase();
  }
  state.cost += estimateCost(response);
  return decision;
}

// ═══════════════════════════════════════════════════════════════
// Guards — three kinds, three jobs
// ═══════════════════════════════════════════════════════════════
// 1. budgetGuard (operational) — steps/cost ceiling. On trip still emits
//    a typed blocked answer without another LLM call.
// 2. plan        (structural)  — LLM proposes, CODE disposes: imperative
//    actions refused pre-LLM, unknown capabilities refused via registry,
//    repeats corrected once then handed to the guard.
// 3. validate    (business)    — required state present & acceptable
//    BEFORE generate_report; writes the blocked report itself.

export const BUDGET = { maxSteps: 10, maxCost: 2.0 };

export function budgetGuard(state) {
  return state.steps >= BUDGET.maxSteps || state.cost >= BUDGET.maxCost;
}

function requiredMissing(state, categories) {
  const needed = [];
  for (const category of categories) {
    for (const field of REQUIREMENTS[category]) {
      if (!needed.includes(field)) needed.push(field);
    }
  }
  return needed.filter((field) => !state[field]);
}

function stepOk(proposal, state, allowed) {
  /** Acceptable only if it's a real, in-scope step whose data isn't
   *  collected yet AND that hasn't already failed this run — retries
   *  live at the transport; the planner must never hammer a broken tool. */
  if (!(proposal in NODE_REGISTRY)) {
    return proposal === "report" || proposal === "done";
  }
  if (!allowed.has(proposal)) return false;
  const failed = new Set(
    state.messages
      .filter((m) => m.status === "failed")
      .map((m) => m.step)
  );
  if (failed.has(NODE_REGISTRY[proposal].node_id)) return false;
  const field = NODE_REGISTRY[proposal].data_field;
  return !state[field];
}

export async function plan(state) {
  /** Planner node: propose next step, validate it against the registry.
   *  The accepted decision lands in state.next_step — the conditional
   *  edge below only READS state. */
  if (budgetGuard(state)) {
    if (!state.report) {
      state.report = blockedAnswer(
        ["AGENT BUDGET EXCEEDED: step/cost ceiling reached before a report was produced"],
        ["Raise the budget, or narrow the query"]
      );
    }
    state.next_step = "stop";
    record(state, "plan", { decision: "stop", reason: "budget exceeded" });
    return state;
  }

  // Deterministic refusal — imperative action, before any LLM call.
  const imperative = state.query.toLowerCase().match(IMPERATIVE_ACTIONS);
  if (imperative) {
    state.next_step = "refuse";
    record(state, "plan", {
      proposal: imperative[1].replace(/\s+/g, "_"),
      decision: "refuse",
      reason: "imperative action — registry check before any LLM call",
    });
    return state;
  }

  // Structural scope: which steps are worth proposing for THIS query?
  const categories = classifyQuery(state.query).split("+");
  const allowed = new Set([
    ...categories.flatMap((c) =>
      REQUIREMENTS[c].map((f) => FIELD_TO_STEP[f]).filter(Boolean)
    ),
    "retrieve",
  ]);

  let proposal = await router(state);
  const known = new Set([...Object.keys(NODE_REGISTRY), "report", "done"]);

  if (!known.has(proposal)) {
    // The model asked for a capability that does not exist → refuse.
    state.next_step = "refuse";
    record(state, "plan", {
      proposal,
      decision: "refuse",
      reason: "not in registry",
    });
    return state;
  }

  if (!stepOk(proposal, state, allowed)) {
    // Already collected, out of scope, or already failed → re-ask ONCE;
    // if the model can't course-correct, the GUARD decides.
    const original = proposal;
    const retry = await router(
      state,
      `'${proposal}' is not appropriate right now — it is either already ` +
        `collected, already failed, or not needed for this query type. ` +
        `Needed steps: ${
          [...allowed].filter((s) => stepOk(s, state, allowed)).join(", ") ||
          "none"
        }. Propose one of those, or 'report'.`
    );
    if (retry in known && stepOk(retry, state, allowed)) {
      proposal = retry;
      state.next_step = proposal;
      record(state, "plan", {
        proposal: original,
        decision: "corrected",
        corrected_to: proposal,
      });
      return state;
    }
    proposal = requiredMissing(state, categories).length === 0 ? "report" : "validate";
    state.next_step = proposal;
    record(state, "plan", {
      proposal: original,
      decision: "fallback",
      corrected_to: proposal,
    });
    return state;
  }

  state.next_step = proposal;
  record(state, "plan", { proposal, decision: "accept" });
  return state;
}

export function routeFromPlan(state) {
  /** The edge is a pure read — plan() already made the decision. */
  return state.next_step;
}

function blockedAnswer(reasons, nextSteps) {
  /** The guard's output: a typed, deterministic answer — not prose. */
  return {
    answer: `Agent stopped before generating a report: ${reasons.join("; ")}`,
    verdict: {
      ready: false,
      confidence: "low",
      blockers: reasons,
      recommended_next_steps: nextSteps,
    },
    evidence: [],
  };
}

export function validate(state) {
  /** Validity guard: is the state acceptable for THIS query's report?
   *  On failure it writes the blocked report itself — typed, zero LLM. */
  const category = classifyQuery(state.query); // label, e.g. "incidents+deploys"
  const categories = category.split("+");
  const reasons = [];
  const nextSteps = [];

  for (const field of requiredMissing(state, categories)) {
    const step = FIELD_TO_STEP[field] || field;
    reasons.push(
      `REQUIRED DATA MISSING: '${field}' was never collected ` +
        `(step '${step}' skipped or failed)`
    );
    nextSteps.push(`Run ${step} before answering this query`);
  }

  if (state.build_status) {
    try {
      const build = JSON.parse(state.build_status);
      if (build.status === "down") {
        const since = build.failing_since ? ` since ${build.failing_since}` : "";
        reasons.push(`BUILD FAILING: status 'down'${since}`);
        nextSteps.push("Fix the failing build before release");
      }
    } catch {
      reasons.push("BUILD STATUS UNPARSEABLE: contract violation in tool output");
      nextSteps.push("Inspect the get_build_status tool output");
    }
  }

  if (reasons.length) {
    state.error = `guard (${category}): ${reasons.join("; ")}`;
    state.report = blockedAnswer(reasons, nextSteps);
    record(state, "validate", { status: "blocked", category });
  } else {
    record(state, "validate", { status: "passed", category });
  }
  return state;
}

export function routeAfterValidate(state) {
  /** Blocked = the guard already wrote the report → stop.
   *  Pass = no report yet → let the model generate one. */
  return state.report ? "end" : "generate_report";
}

export function refuse(state) {
  /** Registry-driven refusal: the message is CONSTRUCTED from the
   *  registry — the model never invents what the agent can do. */
  const proposal =
    [...state.messages]
      .reverse()
      .find((m) => m.step === "plan" && m.proposal)?.proposal || "unknown action";
  const available = Object.keys(NODE_REGISTRY).join(", ");
  state.error = `refused: no registered step for '${proposal}'`;
  state.report = {
    answer: `I can't do that — '${proposal}' is not an available action. DevBuddy can: ${available}.`,
    verdict: {
      ready: false,
      confidence: "low",
      blockers: [`Requested action '${proposal}' has no registered tool`],
      recommended_next_steps: [`Ask for one of: ${available}`],
    },
    evidence: [],
  };
  record(state, "refuse", { action: proposal });
  return state;
}

// ═══════════════════════════════════════════════════════════════
// Graph builders
// ═══════════════════════════════════════════════════════════════

export function buildFixedChain() {
  /** C1: fixed 4-step chain — hardcoded edges, no guard. */
  const graph = new StateGraph({ channels: initState("") });
  graph.addNode("extract_service", extractService);
  graph.addNode("retrieve", retrieveContext);
  graph.addNode("check_build", checkBuild);
  graph.addNode("generate_report", generateReport);
  graph.addEdge("__start__", "extract_service");
  graph.addEdge("extract_service", "retrieve");
  graph.addEdge("retrieve", "check_build");
  graph.addEdge("check_build", "generate_report");
  graph.addEdge("generate_report", END);
  return graph.compile();
}

export function buildGuardedChain(includeBuild = true) {
  /** C3: fixed chain + validity guard before the report.
   *  includeBuild=false reproduces C2's missing-step graph WITH the guard. */
  const graph = new StateGraph({ channels: initState("") });
  graph.addNode("extract_service", extractService);
  graph.addNode("retrieve", retrieveContext);
  graph.addNode("check_deploys", checkDeploys);
  graph.addNode("validate", validate);
  graph.addNode("generate_report", generateReport);
  graph.addEdge("__start__", "extract_service");
  graph.addEdge("extract_service", "retrieve");
  if (includeBuild) {
    graph.addNode("check_build", checkBuild); // unreachable when omitted
    graph.addEdge("retrieve", "check_build");
    graph.addEdge("check_build", "check_deploys");
  } else {
    graph.addEdge("retrieve", "check_deploys");
  }
  graph.addEdge("check_deploys", "validate");
  graph.addConditionalEdges("validate", routeAfterValidate, {
    generate_report: "generate_report",
    end: END,
  });
  graph.addEdge("generate_report", END);
  return graph.compile();
}

export function buildMissingStepAgent() {
  /** C2: check_build REMOVED and NO guard — the naive report node
   *  fills the gap the missing node left behind. */
  const graph = new StateGraph({ channels: initState("") });
  graph.addNode("extract_service", extractService);
  graph.addNode("retrieve", retrieveContext);
  graph.addNode("check_deploys", checkDeploys);
  graph.addNode("generate_report_naive", generateReportNaive);
  graph.addEdge("__start__", "extract_service");
  graph.addEdge("extract_service", "retrieve");
  graph.addEdge("retrieve", "check_deploys");
  graph.addEdge("check_deploys", "generate_report_naive");
  graph.addEdge("generate_report_naive", END);
  return graph.compile();
}

export function buildDynamicAgent() {
  /** Dynamic agent: plan → registry → act, in a loop. One planner node,
   *  ONE conditional edge reading state, validity guard before the report. */
  const graph = new StateGraph({ channels: initState("") });
  graph.addNode("extract_service", extractService);
  graph.addNode("plan", plan);
  graph.addNode("validate", validate);
  graph.addNode("refuse", refuse);
  graph.addNode("generate_report", generateReport);

  for (const [name, spec] of Object.entries(NODE_REGISTRY)) {
    graph.addNode(name, spec.fn);
    graph.addEdge(name, "plan");
  }

  graph.addEdge("__start__", "extract_service");
  graph.addEdge("extract_service", "plan");
  graph.addConditionalEdges("plan", routeFromPlan, PLAN_ROUTE_MAP);
  graph.addConditionalEdges("validate", routeAfterValidate, {
    generate_report: "generate_report",
    end: END,
  });
  graph.addEdge("refuse", END);
  graph.addEdge("generate_report", END);
  return graph.compile();
}

// ═══════════════════════════════════════════════════════════════
// Convenience functions
// ═══════════════════════════════════════════════════════════════

export async function runFixedChain(query) {
  return await buildFixedChain().invoke(initState(query));
}

export async function runDynamicAgent(query) {
  return await buildDynamicAgent().invoke(initState(query));
}

export async function runGuardedChain(query, includeBuild = true) {
  return await buildGuardedChain(includeBuild).invoke(initState(query));
}

export async function runMissingStepAgent(query) {
  return await buildMissingStepAgent().invoke(initState(query));
}