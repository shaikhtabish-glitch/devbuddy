/**
 * Demo 3: Few-shot — the prompt steers the JUDGMENT, the schema fixes the FORMAT.
 *
 * Same PR. Same schema. Two system prompts:
 *   - no few-shot: the model applies its default severity rubric.
 *   - with few-shot: two examples recalibrate that rubric.
 * The format stays valid (BuildCheck) both times; the judgment (severity) is steered.
 *
 * Run: node scripts/week-02/demo-03-few-shot.js
 */
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { getLlm } from "../../src/llm.js";
import { BuildCheckSchema } from "../../src/schemas.js";

const PR_TITLE = "Consolidate error handling across user profile module";
const PR_DIFF = [
  "Moved duplicate try/except blocks from 6 profile endpoints into a shared",
  "error_handler.py decorator. No behavior changes.",
  "Files: src/profiles/error_handler.py, src/profiles/views.py",
].join("\n");

const BASE_PROMPT =
  "You are a code reviewer. Analyze the given PR and return a BuildCheck.\n" +
  "- severity: 'critical' if it touches auth, payments, or security. " +
  "'high' if it changes core logic. 'medium' for feature work. 'low' for docs/typos.\n" +
  "- summary: one sentence describing what changed and why.\n" +
  "- affected_files: list the files mentioned in the diff.\n" +
  "- project: extract the project or service name from the PR context.";

const FEW_SHOT_PROMPT =
  BASE_PROMPT +
  "\n\nHere are examples to calibrate severity:\n" +
  "<example>\n" +
  "PR: 'Consolidated error handling into a shared decorator across 6 endpoints'\n" +
  "severity: high — it touches the core request path of every endpoint.\n" +
  "</example>\n" +
  "<example>\n" +
  "PR: 'Updated the README with setup steps'\n" +
  "severity: low — documentation only.\n" +
  "</example>";

console.log("=".repeat(70));
console.log("  Demo 3: Few-shot — the prompt steers the JUDGMENT");
console.log("=".repeat(70));
console.log();
console.log(`  INPUT (same for both runs): ${PR_TITLE}`);
console.log();

const llm = getLlm({ temperature: 0.0 });
const structured = llm.withStructuredOutput(BuildCheckSchema);

// ── Run 1: no few-shot ─────────────────────────────────────────
console.log("-".repeat(70));
console.log("  RUN 1: default prompt (no examples)");
console.log("-".repeat(70));
console.log();
const r1 = await structured.invoke([
  new SystemMessage(BASE_PROMPT),
  new HumanMessage(`PR Title: ${PR_TITLE}\n\nDiff:\n${PR_DIFF}`),
]);
console.log(`    severity = ${r1.severity}`);
console.log(`    summary  = "${r1.summary}"`);
console.log();

// ── Run 2: with few-shot ───────────────────────────────────────
console.log("-".repeat(70));
console.log("  RUN 2: same prompt + a few-shot example steering severity up");
console.log("-".repeat(70));
console.log();
const r2 = await structured.invoke([
  new SystemMessage(FEW_SHOT_PROMPT),
  new HumanMessage(`PR Title: ${PR_TITLE}\n\nDiff:\n${PR_DIFF}`),
]);
console.log(`    severity = ${r2.severity}`);
console.log(`    summary  = "${r2.summary}"`);
console.log();

console.log("  Same input. Same schema. The FORMAT never changed (both are valid");
console.log("  BuildCheck objects). The JUDGMENT changed: medium → high.");
console.log();
console.log("  Key: the schema guarantees the SHAPE; the prompt (few-shot) steers");
console.log("  the CONTENT. Few-shot for format is redundant once you have a schema —");
console.log("  but few-shot for judgment steers what the model decides.");
console.log("=".repeat(70));
