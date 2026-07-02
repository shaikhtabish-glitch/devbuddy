/**
 * Demo 3: Chunk Size — 256 vs 512 vs 1024
 *
 * Same question, three chunk sizes. Shows how chunking affects:
 *   - Number of chunks (smaller size = more chunks = more embeddings to store)
 *   - Completeness (larger size = more context per chunk)
 *   - Relevance precision (smaller size = more targeted snippets)
 *
 * Run: node scripts/week-03/demo-03-chunk-size.js
 */
import { indexDocuments, retrieve } from "../../src/rag.js";

console.log("=".repeat(70));
console.log("  Demo 3: Chunk Size — 256 vs 512 vs 1024");
console.log("=".repeat(70));
console.log();

const question = "How do I contribute to DevBuddy?";
console.log(`  Question: "${question}"`);
console.log();

for (const size of [256, 512, 1024]) {
  console.log(`  ▸ chunk_size = ${size}`);
  const count = await indexDocuments(null, size, 64);
  const chunks = await retrieve(question, 3);

  // Show top chunk with character counts to compare completeness
  for (let i = 0; i < chunks.length; i++) {
    const preview = chunks[i];
    const charCount = preview.length;
    // Show first meaningful content line after the heading, plus a snippet
    const lines = preview.split("\n").filter((l) => l.trim() && !l.startsWith("#"));
    const snippet = lines.slice(0, 3).join(" ").substring(0, 150);
    console.log(`    [${i + 1}] ${charCount} chars | ${snippet}${snippet.length >= 150 ? "..." : ""}`);
  }
  console.log(`         → ${count} total chunks indexed`);
  console.log();
}

console.log("  Observations:");
console.log("  • chunk_size=256 → 44 chunks. Higher precision but each chunk is small.");
console.log("  • chunk_size=512 → 19 chunks. Good balance of context and relevance.");
console.log("  • chunk_size=1024 → 10 chunks. More context per chunk, fewer chunks total.");
console.log();
console.log("  Key tradeoff: smaller chunks = more targeted retrieval but may");
console.log("  split related content. Larger chunks = more context but less precision.");
console.log("=".repeat(70));
