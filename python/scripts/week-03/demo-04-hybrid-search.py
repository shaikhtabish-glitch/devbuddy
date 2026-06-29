"""
Demo 4: Hybrid Search — Vector vs BM25+RRF (Qdrant Backend)

Compares pure vector retrieval with hybrid (BM25 + RRF fusion)
using the real Qdrant-backed pipeline from src.rag.

Run: python scripts/week-03/demo-04-hybrid-search.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve, hybrid_search

index_documents(chunk_size=512, chunk_overlap=64)

queries = [
    ("how do I set up DevBuddy?", "natural language — vector should dominate"),
    ("error 408", "exact error code — keyword should help"),
]

print("=" * 70)
print("  Demo 4: Hybrid Search — Vector vs BM25+RRF (Qdrant)")
print("=" * 70)
print()

for idx, (question, description) in enumerate(queries, 1):
    vec = retrieve(question, k=5)
    hyb = hybrid_search(question, k=5)

    print(f"  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  RUN {idx}/2 — \"{question}\"")
    print(f"  ║  {description:<58} ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print()

    print(f"  ▸ VECTOR ONLY (semantic):")
    for i, c in enumerate(vec):
        print(f"    [{i+1}] {c.strip().split(chr(10))[0]}")
    print()
    print(f"  ▸ HYBRID (vector + BM25 + RRF):")
    for i, c in enumerate(hyb):
        print(f"    [{i+1}] {c.strip().split(chr(10))[0]}")
    print()

    diff = set(vec) != set(hyb)
    only_hyb = set(hyb) - set(vec)
    only_vec = set(vec) - set(hyb)

    if diff:
        print(f"  ✅ DIFFERENT! Hybrid found {len(only_hyb)} chunk(s) vector missed.")
        for c in only_hyb:
            print(f"     → {c.strip().split(chr(10))[0]}")
    else:
        print(f"  ══ Top-5 identical — with {len(vec)} docs, both agree at this depth.")
        print(f"  At 50+ docs, BM25 surfaces keyword matches vector ignores.")
    print()

print("=" * 70)
print("  Vector  = semantic similarity (what does this MEAN?)")
print("  Hybrid  = semantic + keyword, fused via RRF (best of both)")
print()
print("  Hybrid wins with: error codes, ticket IDs, service names —")
print("  terms with no semantic neighbors. At small scale they agree;")
print("  at production scale they diverge.")
print("=" * 70)
