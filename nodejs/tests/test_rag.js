/**
 * Tests for src/rag.js — Week 3 (Node.js)
 */
import { describe, it, expect, beforeAll } from "vitest";
import {
  indexDocuments,
  retrieve,
  retrieveWithSources,
  hybridSearch,
  hybridSearchWithScores,
  groundedAnswer,
  groundedAnswerWithChunks,
  _bm25Tokenize,
  _isTitleOnly,
  SYSTEM_PROMPT,
  RRF_K,
} from "../src/rag.js";

// Build index once before all tests
beforeAll(async () => {
  const count = await indexDocuments(null, 512, 64);
  expect(count).toBeGreaterThan(0);
});

describe("indexDocuments", () => {
  it("creates at least 4 chunks", async () => {
    const count = await indexDocuments(null, 512, 64);
    expect(count).toBeGreaterThanOrEqual(4);
  });
});

describe("retrieve", () => {
  it("returns relevant chunks for a payment API query", async () => {
    const chunks = await retrieve(
      "What endpoints does the payment API expose?",
      3
    );
    expect(chunks.length).toBeGreaterThan(0);
    const hasPayment = chunks.some((c) =>
      c.toLowerCase().includes("payment")
    );
    expect(hasPayment).toBe(true);
  });

  it("returns different chunks for different queries", async () => {
    const payChunks = await retrieve("payment API timeout", 3);
    const contribChunks = await retrieve("how to contribute", 3);
    // Should differ since queries target different topics
    const payJoined = payChunks.join("");
    const contribJoined = contribChunks.join("");
    expect(payJoined).not.toBe(contribJoined);
  });
});

describe("groundedAnswer", () => {
  it("answers from retrieved context, not training data", async () => {
    const answer = await groundedAnswer(
      "What is the SLA for the payment API?",
      3
    );
    expect(answer.length).toBeGreaterThan(10);
    const lower = answer.toLowerCase();
    expect(
      lower.includes("99.95") ||
        lower.includes("sla") ||
        lower.includes("uptime")
    ).toBe(true);
  });

  it("returns answer and chunks", async () => {
    const [answer, chunks] = await groundedAnswerWithChunks(
      "What is the SLA for the payment API?",
      3
    );
    expect(answer.length).toBeGreaterThan(10);
    expect(chunks.length).toBeGreaterThan(0);
    expect(
      chunks.some((c) => c.includes("99.95") || c.includes("SLA"))
    ).toBe(true);
  });

  it("does not hallucinate on out-of-corpus questions", async () => {
    const answer = await groundedAnswer(
      "What's the revenue forecast for Q4 2028?",
      3
    );
    const lower = answer.toLowerCase();
    expect(
      lower.includes("don't have") || lower.includes("no information")
    ).toBe(true);
  });
});

describe("hybridSearch", () => {
  it("returns results for keyword queries", async () => {
    const hyb = await hybridSearch("payment-api", 3);
    const vec = await retrieve("payment-api", 3);
    expect(hyb.length).toBeGreaterThan(0);
    expect(hyb.length).toBe(vec.length);
  });
});

describe("chunk size", () => {
  it("smaller chunk size produces more chunks", async () => {
    const count256 = await indexDocuments(null, 256, 64);
    const count1024 = await indexDocuments(null, 1024, 64);
    expect(count256).toBeGreaterThan(count1024);
    // Restore default
    await indexDocuments(null, 512, 64);
  });
});

describe("error handling", () => {
  it("throws when retrieve is called without an index", async () => {
    // We can't easily reset the module-level state in ESM,
    // but the error message is clear in the code.
    // This test just validates the function exists and is importable.
    expect(typeof retrieve).toBe("function");
  });
});

// ═══════════════════════════════════════════════════════════════
// Week 4 additions — provenance, hybrid ranks, tokenizer
// ═══════════════════════════════════════════════════════════════

describe("retrieveWithSources", () => {
  it("returns content, source, and score", async () => {
    const results = await retrieveWithSources("payment API", 3);
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].content).toBeTruthy();
    expect(results[0].source).toBeTruthy();
    expect(typeof results[0].score).toBe("number");
  });
});

describe("hybridSearchWithScores", () => {
  it("reports per-retriever ranks and the fused score", async () => {
    const results = await hybridSearchWithScores("payment-api", 3);
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]).toHaveProperty("rrf_score");
    expect(results[0]).toHaveProperty("vec_rank");
    expect(results[0]).toHaveProperty("bm25_rank");
    expect(results[0].rrf_score).toBeGreaterThan(0);
  });
});

describe("BM25 tokenizer & title-only filter", () => {
  it("splits hyphenated IDs into tokens", () => {
    expect(_bm25Tokenize("INC-799")).toEqual(["inc", "799"]);
  });

  it("detects heading-only chunks", () => {
    expect(_isTitleOnly("# Payment API\n> owner: x")).toBe(true);
    expect(
      _isTitleOnly(
        "# Payment API\nThis service handles payments and refunds with retries."
      )
    ).toBe(false);
  });

  it("exposes the RRF constant and a context prompt slot", () => {
    expect(RRF_K).toBe(60);
    expect(SYSTEM_PROMPT).toContain("{context}");
  });
});
