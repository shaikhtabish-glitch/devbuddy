# Tokens, Embeddings, and Context Windows

> Pre-reading for Week 3. 5 minutes.

---

## The Problem

An LLM without access to your data will answer questions about your internal systems by guessing. Confidently. Plausibly. Wrong.

> *"What's the SLA for the inventory service?"*
> → *"99.9% uptime with 4-hour response time."*

This is **hallucination** — not a bug, but the default behaviour. The model predicts the most likely next token. "I don't know" is rarely the most likely token.

---

## The Solution: RAG

**R**etrieval **A**ugmented **G**eneration — four steps:

| Step | What happens |
|------|-------------|
| 1. **Chunk** | Split your documents into pieces (256–1024 tokens each) |
| 2. **Embed** | Convert each chunk into a vector — a list of numbers representing its meaning |
| 3. **Store** | Save those vectors in a database (ChromaDB) |
| 4. **Retrieve** | When a question comes in, embed the question, find the closest chunks, inject them into the prompt |

The model now answers from your data, not its training data.

---

## What Are Embeddings?

Geometric intuition, not math.

Imagine every sentence as a point in space. Sentences with similar meaning are close together:

```
"Login failed"  ←→  "Authentication error"
     │                    │
     │    "Deploy successful"
     │
  "Payment timeout"
```

Embeddings turn text into those coordinates. Retrieval finds the nearest neighbours. You don't need to understand cosine similarity or the transformer architecture to use embeddings — you just need to know: **similar meaning → close in vector space.**

---

## Context Windows Are Scarce Resources

The context window is measured in tokens. Every token costs money and competes for the model's attention.

| Approach | Works for | Breaks at |
|----------|-----------|-----------|
| **Prompt-stuffing** (dump all docs into the prompt) | 3 documents | 300 documents — exceeds context window |
| **RAG** (retrieve only the relevant chunks) | 300 documents | 30,000 documents — but still works, just needs better retrieval |

RAG is the scalable architecture. Don't stuff. Retrieve.

---

## Context Engineering — Retrieval Is Half the Battle

What you do with the retrieved chunks determines answer quality:

- **Assembly order matters:** System prompt → retrieved chunks → conversation history → user query. Chunks in the middle of a long prompt may be ignored — the "lost in the middle" problem.
- **Density matters:** 3 highly relevant chunks > 10 partially relevant chunks. More is not better.
- **Hybrid search matters:** Pure vector = semantic similarity. Add keyword matching (BM25) for exact names, IDs, error codes. "payment-api" might not be close to "payments service" in vector space.

---

## When NOT to Use RAG

- The answer must be exact → use a database query
- The corpus is tiny (< 5 docs) → stuff the prompt (cheaper, simpler)
- Latency is critical → retrieval adds 50–200ms per query

---

## One Question to Hold

Before the session, look at your team's documentation. READMEs, runbooks, wikis, API specs. Ask yourself: *"If someone asked a question about our system that isn't explicitly written down, would it be answered correctly?"*

That gap is where hallucination lives. Today we close it.
