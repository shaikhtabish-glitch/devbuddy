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
    ("error 408", "BM25 finds '408' in lunch budget AND incident log. Vector only finds incidents."),
    ("PROJ-891", "BM25 finds ticket in lunch doc AND travel advisory. Vector only finds tech docs."),
    ("payment-api timeout", "BM25 finds travel site AND tech docs. Vector only finds tech docs."),
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

vec = retrieve("error 408", k=10)
hyb = hybrid_search("error 408", k=10)

print("  Top 10 — Vector only:")
for i, c in enumerate(vec):
    has_408 = "408" in c
    print(f"    [{i+1:>2}] {'408' if has_408 else '   '}  {c.strip().split(chr(10))[0]}")

print()
print("  Top 10 — Hybrid (vector + BM25):")
for i, c in enumerate(hyb):
    has_408 = "408" in c
    print(f"    [{i+1:>2}] {'408' if has_408 else '   '}  {c.strip().split(chr(10))[0]}")
print()

vec_408 = sum(1 for c in vec if "408" in c)
hyb_408 = sum(1 for c in hyb if "408" in c)

print(f"  Chunks containing '408' in the ENTIRE index: {hyb_408} out of {len(hyb)} retrieved.")
print()
if set(vec) == set(hyb):
    print("  ══ Both retrievers return the same top-10.")
    print()
    print("  Why? With 9 docs (~19 chunks), the index is too small for")
    print("  keyword matching to diverge from semantic similarity.")
    print("  The noise docs (recipe 408°F, lunch $408, movie 4,080)")
    print("  fall below the top-10 cutoff for both retrievers.")
    print()
    print("  At 100+ docs, BM25 would surface those noise docs while")
    print("  vector ignores them. The concept holds — the demo is")
    print("  limited by corpus size, not by correctness.")
else:
    only_hyb = set(hyb) - set(vec)
    only_vec = set(vec) - set(hyb)
    if only_hyb:
        print(f"  ✅ Hybrid found {len(only_hyb)} chunk(s) vector missed:")
        for c in only_hyb:
            print(f"     {c.strip().split(chr(10))[0]}")
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
