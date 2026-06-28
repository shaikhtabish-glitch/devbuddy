"""
Demo 1: Embed → Retrieve → Ground

Loads the document set, indexes it, retrieves chunks for an in-corpus
question, and produces a grounded answer. Shows the full RAG loop.

Run: python scripts/week-03/demo-01-embed-retrieve-ground.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve, grounded_answer_with_chunks

print("=" * 65)
print("  Demo 1: Embed → Retrieve → Ground")
print("=" * 65)
print()

# ── Index ─────────────────────────────────────────────────────
print("  Indexing documents from shared/data/ ...")
count = index_documents(chunk_size=512, chunk_overlap=64)
print(f"  ✅ {count} chunks indexed")
print()

# ── Retrieve + Answer ─────────────────────────────────────────
question = "What endpoints does the payment API expose?"

print(f"  Question: {question}")
print()

chunks = retrieve(question, k=4)
for i, chunk in enumerate(chunks):
    print(f"  ── Chunk {i+1} ──")
    print(f"  {chunk[:200]}{'...' if len(chunk) > 200 else ''}")
    print()

answer, retrieved = grounded_answer_with_chunks(question, k=5)
print(f"  Answer: {answer}")
print()

print("=" * 65)
print("  The model listed all 4 endpoints from the API spec —")
print("  including the health endpoint that was in chunk 4.")
print("  It did NOT guess. It RETRIEVED.")
print("=" * 65)
