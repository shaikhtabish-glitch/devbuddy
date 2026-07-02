/**
 * DevBuddy Verification Script — Week 0 (Node.js)
 *
 * This script verifies:
 * 1. OpenRouter connectivity
 * 2. Structured output (LLM returns a typed object, not prose)
 * 3. Cost tracking (token usage from response headers)
 * 4. Your environment is ready for Week 1
 *
 * Run: node src/verification.js
 *
 * This is NOT "Hello World." It's a microcosm of what DevBuddy becomes.
 * By Week 7, this pattern — LLM → structured output → cost tracking —
 * will be the foundation of a complete AI agent.
 */
import "dotenv/config";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { z } from "zod";
import { getLlm } from "./llm.js";

// ─── Configuration ─────────────────────────────────────────────
const MODEL = process.env.DEBUDDY_MODEL || "openai/gpt-4o-mini";

// ─── Schema Definition ─────────────────────────────────────────
// This is a preview of Week 2. Today you just see it work.
const BuildCheckSchema = z.object({
  project: z.string().describe("Project name"),
  status: z
    .enum(["passing", "failing", "in_progress", "unknown"])
    .describe("Build status"),
  confidence: z
    .number()
    .min(0)
    .max(1)
    .describe(
      "Confidence score 0-1. Must be ≤ 1 because this is a DEMO " +
        "with no real CI connection."
    ),
  explanation: z.string().describe("One sentence explaining the result"),
});

/**
 * @typedef {z.infer<typeof BuildCheckSchema>} BuildCheck
 */

// ─── Execution ─────────────────────────────────────────────────
async function main() {
  console.log("=".repeat(60));
  console.log("  DevBuddy Verification — Week 0 (Node.js)");
  console.log("=".repeat(60));
  console.log();

  let llm;
  try {
    llm = getLlm(MODEL, 0.0);
  } catch (e) {
    console.error(`❌ ${e.message}`);
    process.exit(1);
  }

  const structuredLlm = llm.withStructuredOutput(BuildCheckSchema, {
    name: "build_check",
    includeRaw: true,
  });

  const projects = ["auth-service", "api-gateway", "user-service"];
  let totalCost = 0.0;
  let totalTokens = 0;

  for (let i = 0; i < projects.length; i++) {
    const project = projects[i];
    console.log(`[${i + 1}/${projects.length}] Checking: ${project}...`);

    const start = performance.now();

    const response = await structuredLlm.invoke([
      new SystemMessage(
        "You are a build status checker. " +
          "You are being evaluated on your ability to return valid, typed JSON. " +
          "Be honest: you don't have real CI access, so set confidence appropriately. " +
          "Explain WHY you picked the status you did."
      ),
      new HumanMessage(
        `Check the build status of '${project}'.\n` +
          `Return a BuildCheck with:\n` +
          `- project: exactly '${project}'\n` +
          `- status: one of passing/failing/in_progress/unknown\n` +
          `- confidence: 0-1 (be honest — you don't have real CI access)\n` +
          `- explanation: one sentence`
      ),
    ]);

    const elapsed = (performance.now() - start) / 1000;

    // Extract the typed object and token usage
    const result = response.parsed;
    const raw = response.raw;

    // Token usage can appear in different locations depending on LangChain.js version
    const tokenUsage =
      raw?.response_metadata?.token_usage ||
      raw?.response_metadata?.usage ||
      raw?.usage_metadata ||
      {};

    const promptTokens = tokenUsage.prompt_tokens || tokenUsage.input_tokens || 0;
    const completionTokens =
      tokenUsage.completion_tokens || tokenUsage.output_tokens || 0;
    const callTokens = promptTokens + completionTokens;
    totalTokens += callTokens;

    // Cost estimate (GPT-4o-mini via OpenRouter: ~$0.15/M input, ~$0.60/M output)
    const cost = (promptTokens * 0.15 + completionTokens * 0.60) / 1_000_000;
    totalCost += cost;

    console.log(`  Status:      ${result.status}`);
    console.log(`  Confidence:  ${(result.confidence * 100).toFixed(0)}%`);
    console.log(`  Reason:      ${result.explanation}`);
    console.log(
      `  Tokens:      ${callTokens} (${promptTokens} in / ${completionTokens} out)`
    );
    console.log(`  Cost:        $${cost.toFixed(6)}`);
    console.log(`  Time:        ${elapsed.toFixed(2)}s`);
    console.log(
      `  Type:        ${result.constructor.name} ← typed object, not a string!`
    );
    console.log();
  }

  // ─── Summary ───────────────────────────────────────────────
  const now = new Date().toISOString();
  console.log("=".repeat(60));
  console.log("  ✅ VERIFICATION PASSED");
  console.log(`  Runtime:    Node.js ${process.version}`);
  console.log(`  Model:      ${MODEL}`);
  console.log(`  Total tokens: ${totalTokens}`);
  console.log(`  Total cost:   $${totalCost.toFixed(6)}`);
  console.log(`  Date:       ${now}`);
  console.log();
  console.log("  Your environment is ready for Week 1.");
  console.log("  Post this output to #devbuddy-series to confirm.");
  console.log();
  console.log("  What do you want DevBuddy to help you with?");
  console.log("  _______________________________________________");
  console.log("=".repeat(60));
}

main().catch((err) => {
  console.error("❌ Verification failed:", err.message);
  process.exit(1);
});
