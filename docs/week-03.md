# Week 3 — RAG & Context Engineering

**Goal:** Ground the model in your own data so it answers from documents — not from training data hallucinations.

---

## Setup

```bash
# 1. Pull latest code
cd devbuddy && git pull upstream main

# 2. Start Qdrant vector database (required for Week 3+)
docker-compose up -d   # or 'docker compose up -d' if you have the plugin
curl http://localhost:6333/healthz  # → healthz check passed
# Dashboard: http://localhost:6333/dashboard

# 3. Install dependencies
cd python
source .venv/bin/activate
pip install -r requirements.txt
```

Verify you're ready:

```bash
# Week 2 baseline (8 pure-Pydantic tests)
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"

# Week 3 RAG tests (10 tests — requires embedding model download + Qdrant running)
python -m pytest tests/test_rag.py -v

# Full suite (21 tests)
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

---

## What You Have

Open `src/rag.py`. It already contains a full RAG pipeline:

- `index_documents(directory, chunk_size, chunk_overlap)` — loads .md/.txt, chunks, embeds, stores in ChromaDB
- `retrieve(query, k)` — top-k semantic search
- `hybrid_search(query, k)` — BM25 + vector interleaved merge
- `grounded_answer(query, k, temperature)` — retrieve → inject into prompt → LLM answer
- `grounded_answer_with_chunks(query, k, temperature)` — returns answer + chunks for transparency

**Vector store:** Qdrant — runs in Docker (`docker-compose up -d`). Production-grade, cross-language (Python/Node.js/Java). Dashboard at http://localhost:6333/dashboard.

**Embeddings:** `all-MiniLM-L6-v2` via `langchain-huggingface` — local, free, no API cost. Downloaded once on first use (~80MB).

**Import graph:** `rag → llm → config` ✅

## Files You'll Touch
- `src/rag.py` — study the implementation, extend it during hands-on
- `src/llm.py` — already built (`get_llm()` factory)
- `shared/data/` — document set to index

## Document Set (pre-loaded in the repo)
- `shared/data/payment-api-spec.md` — fake API spec: endpoints, auth, error codes, SLA
- `shared/data/inventory-service-sla.md` — grounding document: "No SLA defined"
- `shared/data/CONTRIBUTING.md` — DevBuddy contribution guide (setup, code style, PR process)

## Demo Scripts
- `scripts/week-03/demo-01-embed-retrieve-ground.py` — full RAG loop: index → retrieve → answer
- `scripts/week-03/demo-02-hallucinate-ground.py` — out-of-corpus vs in-corpus (system prompt suppresses hallucination)
- `scripts/week-03/demo-03-chunk-size.py` — same question across 256, 512, 1024 chunk sizes
- `scripts/week-03/demo-04-hybrid-search.py` — vector vs BM25+vector side by side

---

## In-Session Steps

The moderator will run two demos first (embed+retrieve+ground, then hallucinate+fix). Watch them, then follow these steps on your own machine.

> ⚠️ The first embedding model download may take 1–2 minutes. The moderator has pre-downloaded it — your machine may need a moment. Start the download early.

---

### Step 1: Index the document set (10 min)

`src/rag.py` is already implemented. Run the index and explore the code:

```python
from src.rag import index_documents

# Index all .md and .txt files from shared/data/
# Defaults: chunk_size=512, chunk_overlap=64
count = index_documents()
print(f"Indexed {count} chunks")
```

**Check:** After running, visit http://localhost:6333/dashboard — you should see the `devbuddy-docs` collection with chunks.

**Want to understand the implementation?** Open `src/rag.py`. Read `index_documents()` — it uses `DirectoryLoader` → `RecursiveCharacterTextSplitter` → `HuggingFaceEmbeddings` → `QdrantVectorStore`. This is the standard LangChain RAG pattern with a production vector DB. Note the separators: `\n# `, `\n## `, `\n### ` — single `#` is critical for splitting top-level document titles.

---

### Step 2: Retrieve and answer (10 min)

Now query the index. Ask a question that's clearly answered in the documents:

```python
from src.rag import index_documents, retrieve, grounded_answer

# Ensure the index exists (if you skipped Step 1 or restarted your shell)
index_documents()

# Retrieve top-3 chunks for a question
chunks = retrieve("What endpoints does the payment API expose?", k=3)
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {chunk[:100]}...")

# Inject the chunks into a prompt and ask the LLM
answer = grounded_answer("What endpoints does the payment API expose?")
print(answer)
```

The model should answer from the retrieved chunks — not from its training data. Verify: does the answer match the content in `shared/data/payment-api-spec.md`?

> **💡 What does `k` control?** `k` is the number of chunks retrieved. `k=3` is the default — enough for a focused question, but content split across 4+ chunks (like our endpoints list) will be missed. Try `k=4` or `k=5` and compare. Higher `k` = more context, more tokens, more cost. Lower `k` = cheaper but risk missing relevant content. There's no "correct" value — it depends on your document structure and question complexity. Play with it.
>
> **Other knobs worth turning:**
> - **`chunk_overlap`** (default: 64) — how many tokens adjacent chunks share. Higher overlap prevents context from being split across chunk boundaries (e.g., a sentence cut in half). Tradeoff: more redundancy = more chunks to embed and store. Try `overlap=0` vs `overlap=128` and see how retrieval changes.
> - **`temperature`** on `grounded_answer()` — controls how deterministic the LLM answer is. `temperature=0` for factual QA, `temperature=0.7` to see if the model gets creative with the retrieved context (and potentially drifts from it).
> - **The system prompt itself** — open `src/rag.py` and read the `SystemMessage` in `grounded_answer()`. Change "If the context does not contain the answer, say so" to something else. What happens to out-of-corpus questions? The prompt IS the guardrail.

---

### Step 3: Out-of-corpus vs In-corpus (5 min)

Our system prompt tells the model: "If the context does not contain the answer, say so." Test it:

```python
from src.rag import index_documents, grounded_answer_with_chunks

index_documents()  # ensure the index exists

# Out-of-corpus — model should decline, not hallucinate
answer, chunks = grounded_answer_with_chunks(
    "What's the revenue forecast for Q4 2028?", k=3
)
print(f"Answer: {answer}")
# → "I don't have information about that in my knowledge base."
# ✅ System prompt worked. No hallucination.

# In-corpus — model retrieves and answers
answer, chunks = grounded_answer_with_chunks(
    "What's the SLA for the inventory service?", k=3
)
print(f"Answer: {answer}")
for i, c in enumerate(chunks):
    print(f"  Chunk {i+1}: {c[:100]}...")
# → "No SLA is defined for the inventory service."
# ✅ Retrieved from inventory-service-sla.md
```

The system prompt IS the guardrail. Without it, the out-of-corpus question would produce a confident hallucination. With it, the model declines. This is context engineering: you control what the model does when retrieval fails.

---

### Step 4: Vary chunk size (10 min)

Re-index three times with different chunk sizes. Query the same question each time:

```python
for size in [256, 512, 1024]:
    index_documents("../shared/data/", chunk_size=size)
    chunks = retrieve("How do I contribute to DevBuddy?", k=3)
    print(f"\nchunk_size={size}:")
    for i, c in enumerate(chunks):
        print(f"  [{i+1}] {c[:120]}...")
```

**Discussion:** Which chunk size gave the most relevant results? Too small loses context ("Fork the repo..." split across chunks loses "then clone it"). Too large dilutes relevance (a chunk about payment API appears near a contribution question). The sweet spot depends on your document structure.

---

### Step 5: Hybrid search (5 min)

Pure vector = semantic similarity. Hybrid = vector + BM25 keyword, fused via RRF. Error codes and ticket IDs have no semantic meaning — keyword matching catches what vector misses:

```python
from src.rag import index_documents, retrieve, hybrid_search

index_documents()

# Compare on a keyword-heavy query
vec = retrieve("error 408", k=5)
hyb = hybrid_search("error 408", k=5)

print("Vector top-5:")
for i, c in enumerate(vec):
    print(f"  [{i+1}] {c.strip().split(chr(10))[0]}")

print("\nHybrid top-5:")
for i, c in enumerate(hyb):
    print(f"  [{i+1}] {c.strip().split(chr(10))[0]}")
```

With 8 documents, the top-5 may be identical. With 50+ docs, BM25 surfaces keyword matches that vector ignores. The demo script (`scripts/week-03/demo-04-hybrid-search.py`) uses mock data to make the difference visually clear.

---

## Acceptance Criteria
- [ ] `index_documents()` builds a Qdrant collection from `shared/data/` (19 chunks at size=512)
- [ ] `retrieve()` returns relevant chunks for an in-corpus question
- [ ] `grounded_answer()` produces an answer that references the retrieved documents
- [ ] An out-of-corpus question returns "I don't have information about that" (system prompt prevents hallucination)
- [ ] `grounded_answer_with_chunks()` returns both the answer and the retrieved chunks
- [ ] Chunk size 256 produces more chunks than chunk size 1024
- [ ] `hybrid_search()` returns different results than `retrieve()` on keyword-heavy queries

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `RuntimeError: No index found` | Run `index_documents()` first |
| `ConnectionError` on Qdrant | `docker-compose up -d` from repo root (or `docker compose up -d`), then `curl localhost:6333/healthz` |
| Embedding model slow first run | ~80MB download. Let it finish. Subsequent runs are instant. |
| `pip install` fails | Make sure you're in `python/` with `.venv` activated |

---

## Self-Learning (Before Week 4)

> **The take-home is context engineering.** Retrieval is only half the battle. The other half is what you do with the retrieved chunks — and what happens when you get it wrong.

### Part A: Chunk size experiment (rigorous)

Run demo-03 at all three sizes and rate the top-3 chunks for each question using **specific criteria**:

| Criterion | 1 (poor) | 5 (excellent) |
|-----------|----------|---------------|
| **Relevance** | Chunk is about a different topic | Chunk directly answers the question |
| **Completeness** | Single sentence, missing key info | Full context — setup steps, code style, PR rules all present |
| **Noise** | Payment API chunks mixed into a setup question | All chunks from the correct document |

Use these 3 questions (not just one):
1. "How do I set up DevBuddy?"
2. "What are the error codes for the payment API?"
3. "What incidents happened in June 2026?"

Create a comparison table. Which size wins across all three questions? Why?

### Part B: Index your own document

Add a document from your actual team to `shared/data/` — a README, runbook, API spec, or incident report. Index it. Write 3 questions it should answer. Test retrieval quality at 512 tokens. Does RAG answer correctly? What chunk size works best for your document? Document the results.

This is the real test: does RAG work on *your* data, not just ours?

### Part C: Break the guardrail

Open `src/rag.py`. Find the `SystemMessage` in `grounded_answer()`. **Delete the line** that says:

> "If the context does not contain the answer, say 'I don't have information about that in my knowledge base.' Never invent information."

Re-index and ask an out-of-corpus question like *"What's the revenue forecast for Q4 2028?"* The model will now invent a confident, wrong answer. This is hallucination — the default behavior of an unguarded LLM.

Now restore the guardrail and re-run. Document:
- What did the model invent with the guardrail removed?
- What does this tell you about deploying RAG without output validation?
- If you had to ship a RAG feature tomorrow, would you trust the system prompt alone?

### Part D: Cost analysis (concrete)

Run `grounded_answer()` for 10 real questions against the indexed doc set. Log tokens per call using `response.usage_metadata`. Compute the actual cost:

```
cost = (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000
```

Now compute the estimated cost of prompt-stuffing: take the total token count of all 8 documents in `shared/data/` and add it to each query. Compare:

| Approach | Tokens per query (avg) | Cost per 1,000 queries |
|----------|----------------------|------------------------|
| RAG (retrieve k=3) | ? | ? |
| Prompt-stuffing (all docs) | ? | ? |

At what doc set size does RAG become cheaper than stuffing? Extrapolate from your numbers.

---

## Runbook Contribution
Write a 1-paragraph ADR: "We chose chunk size [256/512/1024] for our RAG pipeline because…"
