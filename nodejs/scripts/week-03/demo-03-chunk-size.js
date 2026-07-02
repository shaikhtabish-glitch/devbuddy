/**
 * Demo 3: Chunk Size — 256 vs 512 vs 1024
 *
 * Same question, three chunk sizes. Shows how chunking affects retrieval quality.
 *
 * Run: node scripts/week-03/demo-03-chunk-size.js
 */
import { indexDocuments, retrieve } from "../../src/rag.js";

console.log("=".repeat(70));
console.log("  Demo 3: Chunk Size — 256 vs 512 vs 1024");
console.log("=".repeat(70));
console.log();

const question = "How do I contribute to DevBuddy?";

for (const size of [256, 512, 1024]) {
  console.log(`  Indexing with chunk_size=${size}...`);
  const count = await indexDocuments(null, size, 64);
  console.log(`    → ${count} chunks`);

  const chunks = await retrieve(question, 3);
  console.log(`  Top-3 retrieved chunks:`);
  for (let i = 0; i < chunks.length; i++) {
    console.log(`    [${i + 1}] ${chunks[i]}`);
  }
  console.log();
}

console.log("  Smaller chunks = more chunks, but may lose context.");
console.log("  Larger chunks = fewer chunks, but may dilute relevance.");
console.log("  The sweet spot depends on your document structure.");
console.log("=".repeat(70));
