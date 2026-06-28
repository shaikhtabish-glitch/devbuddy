# Week 3 — RAG & Context Engineering

**Goal:** Ground the model in your own data so it answers from documents — not from training data hallucinations.

---

## Setup

```bash
cd python
source .venv/bin/activate
git pull upstream main          # get latest code + doc set
pip install -r requirements.txt # chromadb + sentence-transformers should be installed
```

Verify you're ready:

```bash
# Week 2 baseline (8 pure-Pydantic tests)
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"

# Week 3 RAG tests (10 tests — requires embedding model download on first run)
python -m pytest tests/test_rag.py -v

# Full suite (21 tests)
python -m pytest tests/ -v --ignore=tests/test_integration.py

python -c "import chromadb; print('ChromaDB OK')"
python -c "from sentence_transformers import SentenceTransformer; print('embeddings OK')"
```

---

## What You Have

Open `src/rag.py`. It already contains a full RAG pipeline:

- `index_documents(directory, chunk_size, chunk_overlap)` — loads .md/.txt, chunks, embeds, stores in ChromaDB
- `retrieve(query, k)` — top-k semantic search
- `hybrid_search(query, k)` — BM25 + vector interleaved merge
- `grounded_answer(query, k, temperature)` — retrieve → inject into prompt → LLM answer
- `grounded_answer_with_chunks(query, k, temperature)` — returns answer + chunks for transparency

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

**Check:** After running, `ls chroma_db/` should show the ChromaDB index files.

**Want to understand the implementation?** Open `src/rag.py`. Read `index_documents()` — it uses `DirectoryLoader` → `RecursiveCharacterTextSplitter` → `HuggingFaceEmbeddings` → `Chroma.from_documents()`. This is the standard LangChain RAG pattern.

---

### Step 2: Retrieve and answer (10 min)

Now query the index. Ask a question that's clearly answered in the documents:

```python
from src.rag import retrieve, grounded_answer

# Retrieve top-3 chunks for a question
chunks = retrieve("What endpoints does the payment API expose?", k=3)
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {chunk[:100]}...")

# Inject the chunks into a prompt and ask the LLM
answer = grounded_answer("What endpoints does the payment API expose?")
print(answer)
```

The model should answer from the retrieved chunks — not from its training data. Verify: does the answer match the content in `shared/data/payment-api-spec.md`?

---

### Step 3: Out-of-corpus vs In-corpus (5 min)

Our system prompt tells the model: "If the context does not contain the answer, say so." Test it:

```python
from src.rag import grounded_answer_with_chunks

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

Pure vector search finds semantic similarity. But keyword matches (BM25) catch exact names, IDs, and error codes:

```python
from src.rag import hybrid_search

# Compare pure vector vs hybrid
vec_chunks = retrieve("payment-api timeout", k=3)
hyb_chunks = hybrid_search("payment-api timeout", k=3)

print("Vector only:")
for c in vec_chunks: print(f"  {c[:100]}...")

print("\nHybrid (vector + BM25):")
for c in hyb_chunks: print(f"  {c[:100]}...")
```

Find one case where hybrid gives a better answer than pure vector. The keyword "payment-api" should boost exact matches that vector-only might miss.

---

## Acceptance Criteria
- [ ] `index_documents()` builds a ChromaDB collection from `shared/data/` (12 chunks at size=512)
- [ ] `retrieve()` returns relevant chunks for an in-corpus question
- [ ] `grounded_answer()` produces an answer that references the retrieved documents
- [ ] An out-of-corpus question returns "I don't have information about that" (system prompt prevents hallucination)
- [ ] `grounded_answer_with_chunks()` returns both the answer and the retrieved chunks
- [ ] Chunk size 256 produces more chunks than chunk size 1024
- [ ] `hybrid_search()` returns different results than `retrieve()` on keyword-heavy queries

---

## Self-Learning (Before Week 4)

> **The take-home is chunking + hybrid search.** You'll compare retrieval quality across chunk sizes and find real cases where hybrid beats pure vector.

### Part A: Chunk size deep-dive
- Index the doc set at 256, 512, and 1024 tokens
- For each, run the same 3 questions and rate the top-3 retrieved chunks (1–5 scale)
- Which size works best? Why? Document your findings.

### Part B: Hybrid search
- Find at least one case where hybrid search gives a demonstrably better answer than pure vector
- The "payment-api timeout" query is a starting point — find your own
- Document why hybrid won: was it keyword matching? acronyms? error codes?

### Part C: Borderline question
- Ask a question that's partially in the corpus, partially not
- Document: (a) where the model hallucinated, (b) what a production system would need to catch this, (c) whether RAG was the right tool or a database query would've been better

### Part D: Cost analysis
- Measure the cost of: embedding N documents + retrieval + LLM call
- Compare to: stuffing all documents into the prompt
- At what corpus size does retrieval become cheaper? (rough math is fine)

---

## Runbook Contribution
Write a 1-paragraph ADR: "We chose chunk size [256/512/1024] for our RAG pipeline because…"
