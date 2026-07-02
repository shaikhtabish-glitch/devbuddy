/**
 * Demo 1: Embed → Retrieve → Ground
 *
 * Full RAG loop: index documents → retrieve chunks → grounded answer.
 * Shows the complete pipeline from raw files to LLM response.
 *
 * Run: node scripts/week-03/demo-01-embed-retrieve-ground.js
 */
import {
  indexDocuments,
  retrieve,
  groundedAnswer,
} from "../../src/rag.js";

console.log("=".repeat(70));
console.log("  Demo 1: Embed → Retrieve → Ground");
console.log("=".repeat(70));
console.log();

// Step 1: Index
console.log("  Indexing documents from shared/data/...");
const count = await indexDocuments(null, 512, 64);
console.log(`  ✅ Indexed ${count} chunks`);
console.log();

// Step 2: Retrieve
console.log("  Retrieving top-3 chunks for: 'What endpoints does the payment API expose?'");
const chunks = await retrieve(
  "What endpoints does the payment API expose?",
  3
);
console.log();
for (let i = 0; i < chunks.length; i++) {
  console.log(`  Chunk ${i + 1}: ${chunks[i]}`);
}
console.log();

// Step 3: Grounded answer
console.log("  Asking LLM with retrieved context...");
const answer = await groundedAnswer(
  "What endpoints does the payment API expose?",
  3
);
console.log(`  Answer: ${answer}`);
console.log();
console.log("  ✅ RAG pipeline complete.");
console.log("=".repeat(70));
