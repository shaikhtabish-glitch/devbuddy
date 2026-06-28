"""
Demo 4: Vector Retrieval — what semantic search finds

Runs three queries through the vector retriever and shows
what chunks come back. Then compares one query with hybrid
search and explains when hybrid would make a difference.

Run: python scripts/week-03/demo-04-hybrid-search.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve, hybrid_search

index_documents(chunk_size=512, chunk_overlap=64)

queries = [
    ("error 408", "exact error code — BM25 finds '408' in incident log"),
    ("PROJ-891", "ticket ID — BM25 exact match, vector has no semantic neighbor"),
    ("payment-api latency", "service + concept — both should work"),
]

print("=" * 70)
print("  Demo 4: Vector Retrieval — What Semantic Search Finds")
print("=" * 70)
print()

for idx, (question, description) in enumerate(queries, 1):
    chunks = retrieve(question, k=3)

    print(f"  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  RUN {idx}/3 — \"{question}\"")
    print(f"  ║  {description:<58} ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print()

    for i, chunk in enumerate(chunks):
        first_line = chunk.strip().split("\n")[0]
        print(f"  [{i+1}] {first_line}")
    print()

# ═══════════════════════════════════════════════════════════════
# Hybrid comparison on a keyword-heavy query
# ═══════════════════════════════════════════════════════════════
print("  ╔══════════════════════════════════════════════════════════════╗")
print("  ║  BONUS: Vector vs Hybrid on \"error 408\"                     ║")
print("  ╚══════════════════════════════════════════════════════════════╝")
print()

vec = retrieve("error 408", k=4)
hyb = hybrid_search("error 408", k=4)

print("  Vector top-4:")
for i, c in enumerate(vec):
    print(f"    [{i+1}] {c.strip().split(chr(10))[0]}")
print()
print("  Hybrid top-4:")
for i, c in enumerate(hyb):
    print(f"    [{i+1}] {c.strip().split(chr(10))[0]}")
print()

if set(vec) == set(hyb):
    print("  ══ Identical — doc set still too small for difference.")
else:
    only_hyb = set(hyb) - set(vec)
    only_vec = set(vec) - set(hyb)
    if only_hyb:
        print(f"  ✅ Hybrid found {len(only_hyb)} chunk(s) vector missed:")
        for c in only_hyb:
            print(f"     {c[:120]}...")
    if only_vec:
        print(f"  Vector found {len(only_vec)} chunk(s) hybrid dropped.")
print()

print("=" * 70)
print("  Vector search = semantic similarity.")
print("  Hybrid search = vector + BM25 keyword matching.")
print()
print("  Where hybrid wins: error codes (408), ticket IDs (PROJ-891),")
print("  service names (payment-api) — terms with no semantic neighbors.")
print("  Where vector wins: natural language questions, concepts,")
print("  summarization — things that mean something, not just match.")
print("=" * 70)
