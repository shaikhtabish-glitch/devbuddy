"""
Demo 4: Hybrid Search — Vector vs BM25+Vector

Compares pure vector retrieval with hybrid (BM25 + vector)
on queries designed to show where each approach wins.

Run: python scripts/week-03/demo-04-hybrid-search.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve, hybrid_search

index_documents(chunk_size=512, chunk_overlap=64)

queries = [
    (
        "error code 402",
        "Exact error code — BM25 finds '402' in payment-api-spec.",
        "Vector may return docs about 'errors' in general.",
    ),
    (
        "Idempotency-Key",
        "Unique header name — only appears in one chunk.",
        "Vector has no semantic match for this specific term.",
    ),
    (
        "how do I set up the project",
        "Natural language — both approaches should work well.",
        "Vector semantic + BM25 keyword both match CONTRIBUTING.md.",
    ),
]

print("=" * 70)
print("  Demo 4: Hybrid Search — Vector vs BM25+Vector")
print("=" * 70)
print()
print("  Each query runs BOTH retrievers side-by-side.")
print("  First line shown for scanability. Full content shown")
print("  when results differ (the interesting case).")
print()

for idx, (question, hybrid_why, vector_why) in enumerate(queries, 1):
    vec = retrieve(question, k=3)
    hyb = hybrid_search(question, k=3)
    diff = set(vec) != set(hyb)

    print(f"  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  RUN {idx}/3 — \"{question}\"")
    print(f"  ╠══════════════════════════════════════════════════════════════╣")
    print(f"  ║  Hybrid wins if:  {hybrid_why:<48} ║")
    print(f"  ║  Vector may:      {vector_why:<48} ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print()

    print(f"  ══ Vector only ══")
    for i, c in enumerate(vec):
        first_line = c.strip().split("\n")[0]
        print(f"  [{i+1}] {first_line}")
    print()

    print(f"  ══ Hybrid (vector + BM25) ══")
    for i, c in enumerate(hyb):
        first_line = c.strip().split("\n")[0]
        print(f"  [{i+1}] {first_line}")
    print()

    if diff:
        print(f"  ✅ HYBRID FOUND DIFFERENT RESULTS!")
        print()
        # Show the chunks that are different
        vec_set = set(vec)
        hyb_set = set(hyb)
        only_hyb = hyb_set - vec_set
        only_vec = vec_set - hyb_set
        if only_hyb:
            print(f"  Chunks ONLY in hybrid (BM25 found these):")
            for c in only_hyb:
                print(f"  ─────────────────────────────────────────────")
                print(f"  {c[:300]}")
        if only_vec:
            print(f"  Chunks ONLY in vector (hybrid dropped these):")
            for c in only_vec:
                print(f"  ─────────────────────────────────────────────")
                print(f"  {c[:300]}")
    else:
        print(f"  ══ Results identical — both approaches agree.")
    print()

print("=" * 70)
print("  Pure vector = semantic similarity (what does this MEAN?).")
print("  Hybrid      = semantic + keyword (what exact WORDS match?).")
print()
print("  Hybrid shines with: error codes, ticket IDs, service names,")
print("  API endpoints, header names — terms with no semantic neighbors.")
print("  At small scale, they often agree. At 100s of docs, hybrid")
print("  catches what vector misses.")
print("=" * 70)
