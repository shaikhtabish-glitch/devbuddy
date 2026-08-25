/**
 * Demo 1: Embed → Retrieve → Ground
 *
 * The full RAG loop, made inspectable:
 *
 *   1. EMBED    — every chunk becomes a vector (a point in space)
 *   2. RETRIEVE — the query is embedded, the closest chunks are returned
 *   3. GROUND   — those SAME chunks are injected into the prompt, and the
 *                 LLM must answer from them
 *
 * The point of this demo is not just to see an answer — it is to see the
 * evidence. Every chunk that grounds the answer is printed with its source,
 * and the prompt the model actually receives is shown.
 *
 * Run: node scripts/week-03/demo-01-embed-retrieve-ground.js
 */
import {
  EMBEDDING_MODEL,
  SYSTEM_PROMPT,
  embedText,
  groundedAnswerFromChunks,
  indexDocuments,
  retrieveWithSources,
} from "../../src/rag.js";

const QUESTION = "What endpoints does the payment API expose?";
const K = 4;
const BORDER = "=".repeat(72);

console.log(BORDER);
console.log("  Demo 1: Embed → Retrieve → Ground");
console.log(BORDER);
console.log();
console.log("  The RAG loop, step by step:");
console.log("    1. EMBED    — each chunk → a vector (a point in space)");
console.log(`                   model: ${EMBEDDING_MODEL} (384-dim vectors)`);
console.log("    2. RETRIEVE — embed the query, return the closest chunks");
console.log("    3. GROUND   — inject those chunks into the prompt, answer");
console.log();
console.log(`  Question: ${QUESTION}`);
console.log();

// ── Step 1: Embed + index ─────────────────────────────────────
console.log("  ── Step 1: Embed & index ────────────────────────────────");
console.log();
console.log("  Each document is split into chunks. Each chunk is embedded");
console.log("  into a vector and stored in Qdrant.");
console.log();
const count = await indexDocuments(null, 512, 64);
console.log(`  ✅ Indexed ${count} chunks → collection 'devbuddy-docs'`);
console.log();

// ── Step 2: Retrieve ──────────────────────────────────────────
console.log("  ── Step 2: Retrieve (top-k by vector similarity) ────────");
console.log();
console.log("  The request — the query — is also embedded into a vector:");
console.log();
console.log(`    "${QUESTION}"`);
const queryVector = await embedText(QUESTION);
const preview = queryVector
  .slice(0, 5)
  .map((v) => Math.round(v * 10000) / 10000);
console.log(
  `    → ${queryVector.length}-dim vector: ${JSON.stringify(preview)} ...`
);
console.log();
console.log(`  Qdrant returns the ${K} chunks whose vectors are closest to`);
console.log("  that query vector, most relevant first. The source of each");
console.log("  chunk is shown so you can trace it back:");
console.log();
const chunks = await retrieveWithSources(QUESTION, K);
chunks.forEach((chunk, i) => {
  console.log(`  [${i + 1}] ${chunk.source}`);
  console.log(`      ${chunk.content}`);
  console.log();
});

// ── Step 3: Ground ────────────────────────────────────────────
console.log("  ── Step 3: Ground (chunks → prompt → LLM) ───────────────");
console.log();
console.log("  The chunks above are injected VERBATIM into the system prompt");
console.log("  as CONTEXT. This is the exact prompt the model receives:");
console.log();
const promptPreview = SYSTEM_PROMPT.replace(
  "{context}",
  `<the ${K} chunks from Step 2, joined with '---'>`
);
for (const line of promptPreview.split("\n")) {
  console.log(`  │ ${line}`);
}
console.log();
console.log("  ── user message ──");
console.log(`  │ ${QUESTION}`);
console.log();

const answer = await groundedAnswerFromChunks(
  QUESTION,
  chunks.map((c) => c.content),
  0.0
);
console.log("  ── answer ──");
console.log(`  │ ${answer}`);
console.log();

// ── Verify ────────────────────────────────────────────────────
console.log(BORDER);
console.log("  Verify the grounding:");
console.log("  every endpoint in the answer should appear in the chunks above.");
console.log("  The chunks are the evidence — check them, not the model's");
console.log("  confidence.");
console.log(BORDER);
