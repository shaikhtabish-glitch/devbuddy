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
    ("payment-api timeout", "exact service name — BM25 catches 'payment-api'"),
    ("how to contribute code", "natural language — vector and BM25 both work"),
    ("PROJ-891", "exact ticket ID — only BM25 finds this, vector has no semantic match"),
]

print("=" * 65)
print("  Demo 4: Hybrid Search — Vector vs BM25+Vector")
print("=" * 65)

for question, description in queries:
    print(f"\n  Query: {question}")
    print(f"  Why:   {description}")
    print(f"  {'─' * 50}")

    vec = retrieve(question, k=3)
    hyb = hybrid_search(question, k=3)

    print(f"  Vector only:")
    for i, c in enumerate(vec):
        print(f"    [{i+1}] {c.strip().split(chr(10))[0]}")

    print()
    print(f"  Hybrid (vector + BM25):")
    for i, c in enumerate(hyb):
        print(f"    [{i+1}] {c.strip().split(chr(10))[0]}")

    diff = set(c for c in vec) != set(c for c in hyb)
    if diff:
        print(f"\n  ✅ Hybrid found different results — keyword matching helped!")
    else:
        print(f"\n  ══ Results identical — keyword didn't change ranking.")

print()
print("=" * 65)
print("  Pure vector = semantic similarity (what does this MEAN?)")
print("  Hybrid      = semantic + keyword (what exact WORDS match?)")
print()
print("  With a small doc set (4 docs), vector and hybrid often")
print("  return the same results. At scale (100s of docs), hybrid")
print("  catches exact IDs, error codes, and service names that")
print("  semantic search would miss.")
print("=" * 65)
