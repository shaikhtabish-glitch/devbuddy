"""
Demo 4: Hybrid Search — vector + BM25 side by side

Compares pure vector retrieval with hybrid (BM25 + vector)
on a query with exact keywords. Shows where hybrid wins.

Run: python scripts/week-03/demo-04-hybrid-search.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve, hybrid_search

index_documents(chunk_size=512, chunk_overlap=64)

queries = [
    "payment-api timeout",
    "how to contribute code",
    "SLA for payments",
]

print("=" * 65)
print("  Demo 4: Hybrid Search — Vector vs BM25+Vector")
print("=" * 65)

for question in queries:
    print(f"\n  Query: {question}")
    print(f"  {'─' * 50}")

    vec = retrieve(question, k=3)
    hyb = hybrid_search(question, k=3)

    print(f"  Vector only:")
    for i, c in enumerate(vec):
        print(f"    [{i+1}] {c[:120]}...")

    print(f"  Hybrid (vector + BM25):")
    for i, c in enumerate(hyb):
        print(f"    [{i+1}] {c[:120]}...")

    # If results differ, hybrid found something vector missed
    if vec != hyb:
        print(f"  ✅ Hybrid found different results — keyword matching helped!")

print()
print("=" * 65)
print("  Pure vector = semantic similarity.")
print("  Hybrid      = semantic + keyword (catches names, IDs, codes).")
print("  Use hybrid when your queries include specific terms.")
print("=" * 65)
