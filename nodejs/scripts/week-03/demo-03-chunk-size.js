/**
 * Demo 3: Chunk Size — 256 vs 512 vs 1024
 *
 * Same question, three chunk sizes. Each run re-indexes the entire doc set.
 * Shows how chunking affects retrieval quality and what gets returned.
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

  for (let i = 0; i < chunks.length; i++) {
    const text = chunks[i];
    console.log(`    [${i + 1}] ${text.length} chars`);
    // Show first non-empty lines (up to 250 chars)
    const lines = text.split("\n").filter((l) => l.trim());
    for (const line of lines.slice(0, 5)) {
      console.log(`        ${line.substring(0, 80)}`);
    }
    if (text.length > 250) console.log(`        ... (${text.length - 250} more chars)`);
    console.log();
  }
  console.log(`    → ${count} total chunks in index`);
  console.log();
}

console.log("  What to look for:");
console.log("  • 256: many small chunks. The top result may be just a heading");
console.log("         with no body — the separator splits title from content.");
console.log("  • 512: moderate chunks. Most headings stay with their body text.");
console.log("  • 1024: fewer large chunks. More context but less targeted.");
console.log("=".repeat(70));
