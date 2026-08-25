/**
 * Demo 2: Hallucinate → Ground
 *
 * The system prompt is the guardrail. This demo proves it by holding the
 * question AND the retrieved chunks fixed, and changing only the system prompt:
 *
 *   1. OUT-OF-CORPUS + guardrail   → the model declines
 *   2. OUT-OF-CORPUS, no guardrail → the model hallucinates
 *   3. IN-CORPUS + guardrail       → the model answers from the chunks
 *
 * Run: node scripts/week-03/demo-02-hallucinate-ground.js
 */
import {
  NO_GUARDRAIL_PROMPT,
  SYSTEM_PROMPT,
  answerWithContext,
  indexDocuments,
  retrieveWithSources,
} from "../../src/rag.js";

const OUT_OF_CORPUS = "What's the revenue forecast for Q4 2028?";
const IN_CORPUS = "How do I contribute code to DevBuddy?";
const K = 3;
const BORDER = "=".repeat(72);

console.log(BORDER);
console.log("  Demo 2: Hallucinate → Ground");
console.log(BORDER);
console.log();

await indexDocuments(null, 512, 64);
console.log("  ✅ Index ready");
console.log();

// ── The out-of-corpus retrieval ───────────────────────────────
// WHY does the retriever return "random" info for an out-of-corpus
// question ("Q4 2028 revenue") instead of nothing?
//
// Because vector search is a top-k nearest-neighbour query: it ALWAYS
// returns k chunks and has no "not found" concept and no relevance
// cutoff. For this question the query vector points into an empty
// region of vector space, so the "nearest" chunks are still far away
// (scores ~0.30 / 0.27 / 0.22, vs ~0.60 for an in-corpus question)
// and happen to be about payments, incidents and SLAs.
//
// Similarity is a RELATIVE ranking, not an ABSOLUTE relevance
// judgement: Qdrant sorts everything by distance and hands back the
// top-k. It never says "0.22 is too low to be useful — nothing
// matched". That decision is left to the guardrail below.
console.log(`  Out-of-corpus question: "${OUT_OF_CORPUS}"`);
console.log();
console.log(`  The retriever always returns its top-${K} chunks — even when none`);
console.log("  of them answer the question:");
console.log();
const chunks = await retrieveWithSources(OUT_OF_CORPUS, K);
chunks.forEach((chunk, i) => {
  console.log(`  [${i + 1}] ${chunk.source}`);
  console.log(`      ${chunk.content}`);
  console.log();
});
console.log('  None of these mention Q4 2028 revenue. Retrieval can\'t return');
console.log('  "nothing" — it returns its best (irrelevant) guess.');
console.log();

// ── With the guardrail ────────────────────────────────────────
console.log("  ── With the guardrail ───────────────────────────────────");
console.log();
console.log("  The system prompt tells the model to decline when the context");
console.log("  doesn't contain the answer:");
console.log();
for (const line of SYSTEM_PROMPT.replace(
  "{context}",
  `<the ${K} chunks above>`
).split("\n")) {
  console.log(`  │ ${line}`);
}
console.log();
const guarded = await answerWithContext(
  OUT_OF_CORPUS,
  chunks.map((c) => c.content),
  SYSTEM_PROMPT
);
console.log(`  Answer: ${guarded}`);
console.log();

// ── Without the guardrail ─────────────────────────────────────
console.log("  ── Without the guardrail ────────────────────────────────");
console.log();
console.log("  Same question, same chunks — but the decline instruction is gone:");
console.log();
for (const line of NO_GUARDRAIL_PROMPT.replace(
  "{context}",
  `<the ${K} chunks above>`
).split("\n")) {
  console.log(`  │ ${line}`);
}
console.log();
const unguarded = await answerWithContext(
  OUT_OF_CORPUS,
  chunks.map((c) => c.content),
  NO_GUARDRAIL_PROMPT
);
console.log(`  Answer: ${unguarded}`);
console.log();

// ── In-corpus ─────────────────────────────────────────────────
console.log("  ── In-corpus (grounded) ─────────────────────────────────");
console.log();
console.log(`  Question: "${IN_CORPUS}"`);
console.log();
const groundedChunks = await retrieveWithSources(IN_CORPUS, K);
groundedChunks.forEach((chunk, i) => {
  console.log(`  [${i + 1}] ${chunk.source}`);
  console.log(`      ${chunk.content}`);
  console.log();
});
const grounded = await answerWithContext(
  IN_CORPUS,
  groundedChunks.map((c) => c.content),
  SYSTEM_PROMPT
);
console.log(`  Answer: ${grounded}`);
console.log();

console.log(BORDER);
console.log("  Same retriever. Same chunks. Only the system prompt changed.");
console.log("  The guardrail is what separates a hallucination from a refusal.");
console.log(BORDER);
