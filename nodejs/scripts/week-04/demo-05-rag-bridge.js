/**
 * Demo 5: RAG as a Tool — the composition pattern
 *
 * THE POINT OF THIS DEMO: a tool is just data with a name. The model does
 * not care whether the data came from a hardcoded dict or your Week-3
 * vector store. Where data comes from is an implementation detail.
 *
 * This tool calls src/rag.retrieve() (the Week-3 pipeline) and asks the LLM
 * to extract an answer from the retrieved chunks — wrapped as a normal tool
 * the model can route to.
 *
 * Run: node scripts/week-04/demo-05-rag-bridge.js      (needs Qdrant running)
 */
import { z } from "zod";
import { tool } from "@langchain/core/tools";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { indexDocuments, retrieve } from "../../src/rag.js";
import { executeToolSafely } from "../../src/tools.js";
import { getLlm } from "../../src/llm.js";
import { BORDER, pause } from "./_common.js";

// Ensure the Week-3 index exists before the demo tool runs.
await indexDocuments(null, 512, 64);

console.log(BORDER);
console.log("  Demo 5: RAG as a Tool — a tool is just data with a name");
console.log(BORDER);
console.log();

// ── Define the tool ────────────────────────────────────────────
// The interface is identical to get_build_status: name, args, JSON return.
// The DATA SOURCE is different — Week 3's vector store, not a dict.

async function ragBuildStatus(serviceName) {
  const chunks = await retrieve(`${serviceName} build status health deploy`, 5);
  if (chunks.length === 0) {
    return JSON.stringify({ status: "unknown", error: `No docs for '${serviceName}'` });
  }

  const context = chunks.join("\n\n");
  const llm = getLlm({ temperature: 0.0 });
  const response = await llm.invoke([
    new SystemMessage(
      "Extract the build/health status from the context. Return JSON with " +
        "'status' (healthy/degraded/down/unknown) and 'last_deploy' (timestamp). " +
        "Only use data from the context."
    ),
    new HumanMessage(`Service: ${serviceName}\n\nContext:\n${context}`),
  ]);
  const text = String(response.content).trim();
  // The model may wrap JSON in prose — try to salvage a JSON object.
  try {
    return JSON.stringify(JSON.parse(text));
  } catch {
    return text;
  }
}

const getBuildStatusFromDocs = tool(
  async ({ service_name }) => ragBuildStatus(service_name),
  {
    name: "get_build_status_from_docs",
    description: "Return the build/health status of a service by searching our knowledge base.",
    schema: z.object({ service_name: z.string() }),
  }
);

console.log("  The tool:");
console.log("    get_build_status_from_docs(service_name)  →  status JSON");
console.log("    data source: retrieve() from src/rag (Week 3) + LLM extraction");
console.log();
console.log("  Compare with src/tools.getBuildStatus — SAME interface, different");
console.log("  data source. Nothing else in the stack changed.");
console.log();

// ── Use it through the app layer, like any other tool ──────────
const toolCall = {
  name: "get_build_status_from_docs",
  args: { service_name: "payment-api" },
};
console.log("  ⏸  PAUSE & PREDICT: our mock dict had payment-api as 'degraded'.");
console.log("     What will the DOCS say? Predict, then continue.");
await pause("  ⏸  Press Enter to run the tool… ");
console.log();

const registry = { get_build_status_from_docs: getBuildStatusFromDocs };
const result = await executeToolSafely(toolCall, 2, { toolsByName: registry });
console.log(`  Tool returned: ${result}`);
console.log();

console.log(BORDER);
console.log("  THE COMPOSITION PATTERN: the orchestrator (Week 6) does not care");
console.log("  whether a tool's data comes from a dict, an API, or a vector store.");
console.log("  A tool is a contract: name + args + JSON out. Source is a detail.");
console.log();
console.log("  YOUR TURN:");
console.log("    • Point get_recent_deploys from docs too — same pattern.");
console.log("    • Add a 'min_score' guard inside the tool so a weak retrieval");
console.log("      returns a structured 'no match', not a guess.");
console.log(BORDER);
