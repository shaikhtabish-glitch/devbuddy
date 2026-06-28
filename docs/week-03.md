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
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"
# Should show 8 tests passing (Week 2 baseline still holds)

python -c "import chromadb; print('ChromaDB OK')"
python -c "from sentence_transformers import SentenceTransformer; print('embeddings OK')"
```

---

## What You Have

Open `src/rag.py`. It's currently a stub. By the end of this session, it will:

- Load documents from `shared/data/`
- Split them into configurable chunks
- Embed chunks with `sentence-transformers` (all-MiniLM-L6-v2 — local, free, no API cost)
- Store in ChromaDB (local vector database)
- Retrieve the top-k chunks for a query
- Assemble context in the right order (system prompt → chunks → user query)
- Answer questions grounded strictly in the retrieved context

## Files You'll Touch
- `src/rag.py` — your implementation (imports `src/llm`)
- `src/llm.py` — already built (`get_llm()` factory)
- `shared/data/` — document set to index

## Document Set (pre-loaded in the repo)
- `shared/data/README.md` — DevBuddy project overview
- `shared/data/CONTRIBUTING.md` — contribution guide
- `shared/data/payment-api-spec.md` — fake API spec for the payments service
- `shared/data/inventory-service-sla.md` — grounding document that prevents hallucination

---

## In-Session Steps

The moderator will run two demos first (embed+retrieve+ground, then hallucinate+fix). Watch them, then follow these steps on your own machine.

> ⚠️ The first embedding model download may take 1–2 minutes. The moderator has pre-downloaded it — your machine may need a moment. Start the download early.

---

### Step 1: Index the document set (10 min)

`src/rag.py` is a stub. Build the core pipeline:

```python
from src.rag import index_documents, retrieve

# Load all .md and .txt files from shared/data/
# Split into chunks (default: 512 tokens with 64-token overlap)
# Embed with sentence-transformers (all-MiniLM-L6-v2)
# Store in ChromaDB collection "devbuddy-docs"
index_documents("../shared/data/", chunk_size=512, chunk_overlap=64)
```

**Stuck?** Here's the skeleton:

```python
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def index_documents(directory: str, chunk_size: int = 512, chunk_overlap: int = 64):
    # 1. Walk directory, read .md and .txt files
    # 2. RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    # 3. HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    # 4. Chroma.from_documents(docs, embeddings, persist_directory="./chroma_db")
    pass
```

**Check:** After running, `ls chroma_db/` should show the ChromaDB index files.

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

### Step 3: Trigger a hallucination (5 min)

Ask a question that's **not** in any document:

```python
answer = grounded_answer("What's the SLA for the inventory service?")
print(answer)
# The model will invent an SLA. "99.9% uptime." Confident. Wrong.
```

Now add the grounding document. Open `shared/data/inventory-service-sla.md`. It says "No SLA defined." Re-index, re-ask:

```python
index_documents("../shared/data/")  # re-index with the new doc
answer = grounded_answer("What's the SLA for the inventory service?")
print(answer)
# Now: "No SLA is defined for the inventory service."
```

**The hallucination is suppressed.** But this only works if the grounding document exists and is retrieved. If retrieval misses it, the model hallucinates again.

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
- [ ] `index_documents()` builds a ChromaDB collection from `shared/data/`
- [ ] `retrieve()` returns relevant chunks for an in-corpus question
- [ ] `grounded_answer()` produces an answer from the retrieved context
- [ ] An out-of-corpus question triggers a hallucination
- [ ] Adding a grounding document suppresses the hallucination
- [ ] Chunk size 256, 512, and 1024 produce different retrieval quality
- [ ] Hybrid search beats pure vector on at least one query

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
