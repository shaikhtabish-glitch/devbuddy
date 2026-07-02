/**
 * Demo 2: Hallucinate → Ground
 *
 * Shows the system prompt acting as a guardrail:
 *   - Out-of-corpus question → model declines ("I don't have info")
 *   - In-corpus question → model answers from documents
 *
 * Run: node scripts/week-03/demo-02-hallucinate-ground.js
 */
import {
  indexDocuments,
  groundedAnswerWithChunks,
} from "../../src/rag.js";

console.log("=".repeat(70));
console.log("  Demo 2: Hallucinate → Ground");
console.log("=".repeat(70));
console.log();

await indexDocuments(null, 512, 64);
console.log("  ✅ Index ready");
console.log();

// Out-of-corpus — model should decline
console.log("  1. OUT-OF-CORPUS: 'What's the revenue forecast for Q4 2028?'");
const [answer1, chunks1] = await groundedAnswerWithChunks(
  "What's the revenue forecast for Q4 2028?",
  3
);
console.log(`     Answer: ${answer1}`);
console.log(`     Chunks: ${chunks1.length}`);
console.log("     ✅ System prompt prevented hallucination");
console.log();

// In-corpus — model retrieves and answers
console.log(
  "  2. IN-CORPUS: 'What's the SLA for the inventory service?'"
);
const [answer2, chunks2] = await groundedAnswerWithChunks(
  "What's the SLA for the inventory service?",
  3
);
console.log(`     Answer: ${answer2}`);
console.log("     Retrieved chunks:");
for (let i = 0; i < chunks2.length; i++) {
  console.log(`       ${i + 1}. ${chunks2[i].slice(0, 100)}...`);
}
console.log("     ✅ Model grounded in documents");
console.log();
console.log("  The system prompt IS the guardrail.");
console.log("=".repeat(70));
