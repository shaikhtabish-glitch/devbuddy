/**
 * Demo 3: Chunk Size — 256 vs 512 vs 1024
 *
 * Same question, three chunk sizes. Each run re-indexes the entire doc set.
 * Shows how chunking affects retrieval quality and what gets returned.
 *
 * Run: node scripts/week-03/demo-03-chunk-size.js
 */
import { indexDocuments, retrieve } from "../../src/rag.js";

// Helper for clean box drawing
function drawBox(title, contentLines) {
  const width = 76;
  const border = "─".repeat(width);
  console.log(`    ┌${border}┐`);
  console.log(`    │ \x1b[1m${title.padEnd(width - 2)}\x1b[0m │`);
  console.log(`    ├${border}┤`);
  for (const line of contentLines) {
    const cleanLine = line.replace(/\r?\n|\r/g, " ").substring(0, width - 4);
    console.log(`    │   ${cleanLine.padEnd(width - 4)} │`);
  }
  console.log(`    └${border}┘`);
}

function analyzeChunk(text) {
  const trimmed = text.trim();
  if (trimmed.length < 50 && (trimmed.startsWith('#') || trimmed.includes('##'))) {
    return "⚠️  [Header-Only Chunk] High keyword match, but contains zero body context.";
  } else if (trimmed.length < 150) {
    return "💡 [Light Context] High precision, but may lack surrounding detail.";
  } else {
    return "✅ [Rich Context] Good balance of headers and actionable detail.";
  }
}

console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
console.log("  \x1b[1m\x1b[35mDevBuddy RAG Diagnostic — Chunk Size Evaluation Demo\x1b[0m");
console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
console.log();
console.log("  This evaluation re-indexes the documentation corpus using three different");
console.log("  chunk sizes (256, 512, and 1024 tokens) to illustrate the trade-off");
console.log("  between retrieval precision and context retention.");
console.log();

const question = "How do I contribute to DevBuddy?";
console.log(`  \x1b[1mQuestion to Retrieve For:\x1b[0m "${question}"`);
console.log();

for (const size of [256, 512, 1024]) {
  console.log(`  \x1b[1m\x1b[32m▸ Evaluating Chunk Size = ${size} tokens (64 token overlap)\x1b[0m`);
  console.log(`    Re-indexing document corpus...`);
  const count = await indexDocuments(null, size, 64);
  console.log(`    Done. Index contains ${count} total chunks.`);
  console.log();

  const chunks = await retrieve(question, 3);

  for (let i = 0; i < chunks.length; i++) {
    const text = chunks[i];
    const lines = text.split("\n").filter((l) => l.trim());
    
    const rankTitle = `Result #${i + 1} (${text.length} chars)`;
    drawBox(rankTitle, lines.slice(0, 5));
    
    const insight = analyzeChunk(text);
    console.log(`       \x1b[33m${insight}\x1b[0m`);
    console.log();
  }
  console.log(`  ${"─".repeat(76)}`);
  console.log();
}

console.log("\x1b[1m\x1b[36mSummary & Key Takeaways:\x1b[0m");
console.log("  • \x1b[1m256 Tokens (Small):\x1b[0m High granularity. Yields many small chunks. The top");
console.log("    results are often bare headers (e.g. '# Contributing to DevBuddy') with no");
console.log("    actual body content, because formatting separators split them early.");
console.log("  • \x1b[1m512 Tokens (Medium):\x1b[0m Balanced context. Most headings remain attached to");
console.log("    their subsequent list items or code block instructions.");
console.log("  • \x1b[1m1024 Tokens (Large):\x1b[0m High context, low precision. Fewer total chunks in the");
console.log("    index. Returns massive blocks of text that consume extra LLM tokens.");
console.log("\x1b[36m" + "=".repeat(80) + "\x1b[0m");
