"""
Demo 1: Embed → Retrieve → Ground

The full RAG loop, made inspectable:

  1. EMBED    — every chunk becomes a vector (a point in space)
  2. RETRIEVE — the query is embedded, the closest chunks are returned
  3. GROUND   — those SAME chunks are injected into the prompt, and the
                LLM must answer from them

The point of this demo is not just to see an answer — it is to see the
evidence. Every chunk that grounds the answer is printed with its source,
and the prompt the model actually receives is shown.

Run: python scripts/week-03/demo-01-embed-retrieve-ground.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import (
    EMBEDDING_MODEL,
    SYSTEM_PROMPT,
    embed_text,
    grounded_answer_from_chunks,
    index_documents,
    retrieve_with_sources,
)

QUESTION = "What endpoints does the payment API expose?"
K = 4

BORDER = "=" * 72

print(BORDER)
print("  Demo 1: Embed → Retrieve → Ground")
print(BORDER)
print()
print("  The RAG loop, step by step:")
print("    1. EMBED    — each chunk → a vector (a point in space)")
print(f"                   model: {EMBEDDING_MODEL} (384-dim vectors)")
print("    2. RETRIEVE — embed the query, return the closest chunks")
print("    3. GROUND   — inject those chunks into the prompt, answer")
print()
print(f"  Question: {QUESTION}")
print()

# ── Step 1: Embed + index ─────────────────────────────────────
print("  ── Step 1: Embed & index ────────────────────────────────")
print()
print("  Each document is split into chunks. Each chunk is embedded")
print("  into a vector and stored in Qdrant.")
print()
count = index_documents(chunk_size=512, chunk_overlap=64)
print(f"  ✅ Indexed {count} chunks → collection 'devbuddy-docs'")
print()

# ── Step 2: Retrieve ──────────────────────────────────────────
print("  ── Step 2: Retrieve (top-k by vector similarity) ────────")
print()
print("  The request — the query — is also embedded into a vector:")
print()
print(f'    "{QUESTION}"')
query_vector = embed_text(QUESTION)
print(f"    → {len(query_vector)}-dim vector: "
      f"{[round(v, 4) for v in query_vector[:5]]} ...")
print()
print(f"  Qdrant returns the {K} chunks whose vectors are closest to")
print("  that query vector, most relevant first. The source of each")
print("  chunk is shown so you can trace it back:")
print()
chunks = retrieve_with_sources(QUESTION, k=K)
for i, chunk in enumerate(chunks, 1):
    print(f"  [{i}] {chunk.source}")
    print(f"      {chunk.content}")
    print()

# ── Step 3: Ground ────────────────────────────────────────────
print("  ── Step 3: Ground (chunks → prompt → LLM) ───────────────")
print()
print("  The chunks above are injected VERBATIM into the system prompt")
print("  as CONTEXT. This is the exact prompt the model receives:")
print()
prompt_preview = SYSTEM_PROMPT.format(
    context=f"<the {K} chunks from Step 2, joined with '---'>"
)
for line in prompt_preview.splitlines():
    print(f"  │ {line}")
print()
print("  ── user message ──")
print(f"  │ {QUESTION}")
print()

answer = grounded_answer_from_chunks(QUESTION, [c.content for c in chunks], temperature=0.0)
print("  ── answer ──")
print(f"  │ {answer}")
print()

# ── Verify ────────────────────────────────────────────────────
print(BORDER)
print("  Verify the grounding:")
print("  every endpoint in the answer should appear in the chunks above.")
print("  The chunks are the evidence — check them, not the model's")
print("  confidence.")
print(BORDER)
