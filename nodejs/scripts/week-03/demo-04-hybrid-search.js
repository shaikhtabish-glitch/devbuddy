/**
 * Demo 4: Hybrid Search — Vector vs BM25+Vector
 *
 * Compares pure vector search with hybrid (BM25 + vector + RRF fusion).
 * Keyword matching catches what vector search misses.
 *
 * Run: node scripts/week-03/demo-04-hybrid-search.js
 */
import { indexDocuments, retrieve, hybridSearch } from "../../src/rag.js";

console.log("=".repeat(70));
console.log("  Demo 4: Hybrid Search — Vector vs BM25+Vector");
console.log("=".repeat(70));
console.log();

await indexDocuments(null, 512, 64);
console.log("  ✅ Index ready");
console.log();

const query = "error 408";
console.log(`  Query: "${query}"`);
console.log();

// Pure vector
const vec = await retrieve(query, 5);
console.log("  Pure Vector top-5:");
for (let i = 0; i < vec.length; i++) {
  const firstLine = vec[i].trim().split("\n")[0];
  console.log(`    [${i + 1}] ${firstLine}`);
}
console.log();

// Hybrid
const hyb = await hybridSearch(query, 5);
console.log("  Hybrid (BM25 + Vector) top-5:");
for (let i = 0; i < hyb.length; i++) {
  const firstLine = hyb[i].trim().split("\n")[0];
  console.log(`    [${i + 1}] ${firstLine}`);
}
console.log();

console.log("  With 8 documents, results may be similar.");
console.log(
  "  With 50+ docs, BM25 surfaces keyword matches vector ignores."
);
console.log("=".repeat(70));
