/**
 * Demo 1: Prose → crash, then Schema → success.
 *
 * The moderator's "Demo 1": call the LLM with a plain prompt and get prose
 * back, feed that prose to JSON.parse() → crash. Then add a schema constraint
 * (analyzePr) and get a typed object back.
 *
 * Run: node scripts/week-02/demo-01-prose-vs-structured.js
 */
import { HumanMessage } from "@langchain/core/messages";
import { getLlm } from "../../src/llm.js";
import { analyzePr } from "../../src/llm_functions.js";

const PR_TITLE = "Fix login redirect loop in auth-service";
const PR_DIFF = [
  "Changed session token validation in src/auth.py lines 42-58.",
  "Previously expired tokens caused infinite redirect for 15% of users.",
  "Now returns 401 with clear error. No DB changes. Rollback: revert commit.",
  "Files: src/auth.py, tests/test_auth.py",
].join("\n");

console.log("=".repeat(70));
console.log("  Demo 1: Prose → crash, then Schema → success");
console.log("=".repeat(70));
console.log();
console.log(`  INPUT: ${PR_TITLE}`);
for (const line of PR_DIFF.split("\n")) {
  console.log(`         ${line}`);
}
console.log();

// ═══════════════════════════════════════════════════════════════
// Step 1: plain prompt → prose
// ═══════════════════════════════════════════════════════════════
console.log("-".repeat(70));
console.log("  STEP 1: plain prompt → prose");
console.log("-".repeat(70));
console.log();

const llm = getLlm({ temperature: 0.0 });
const raw = (
  await llm.invoke([
    new HumanMessage(`Summarize this PR: ${PR_TITLE}\n\n${PR_DIFF}`),
  ])
).content;

console.log("  Raw response:");
for (const line of raw.trim().split("\n")) {
  console.log(`  | ${line}`);
}
console.log();

// ═══════════════════════════════════════════════════════════════
// Step 2: JSON.parse → crash
// ═══════════════════════════════════════════════════════════════
console.log("-".repeat(70));
console.log("  STEP 2: JSON.parse(raw) → crash");
console.log("-".repeat(70));
console.log();

try {
  const data = JSON.parse(raw);
  console.log(`  ✅ parsed unexpectedly: ${Object.keys(data).join(", ")}`);
} catch (e) {
  console.log(`  ❌ CRASHED: ${e.message}`);
  console.log();
  console.log("  This is code slop. Free text breaks pipelines. Let's fix it.");
}
console.log();

// ═══════════════════════════════════════════════════════════════
// Step 3: schema constraint → typed object
// ═══════════════════════════════════════════════════════════════
console.log("-".repeat(70));
console.log("  STEP 3: analyzePr (schema-constrained) → typed object");
console.log("-".repeat(70));
console.log();

const result = await analyzePr({
  title: PR_TITLE,
  diff: PR_DIFF,
  temperature: 0.0,
});

console.log(`  type: ${result.constructor.name}  ← typed object, not prose!`);
console.log();
console.log(JSON.stringify(result, null, 2));
console.log();

console.log("=".repeat(70));
console.log("  The LLM is now a typed function.");
console.log("  Input → BuildCheck. Your code consumes it directly.");
console.log("=".repeat(70));
