"""
Demo 4: Vector vs Hybrid Search — Pro, Con, Combined

Three runs that build on each other:
  RUN 1 (PRO):   Vector search on a natural language query — works perfectly.
  RUN 2 (CON):   Vector search on an exact keyword — may miss specific matches.
  RUN 3 (COMBO): Same keyword query, vector vs hybrid side-by-side.

Run: python scripts/week-03/demo-04-hybrid-search.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve, hybrid_search

index_documents(chunk_size=512, chunk_overlap=64)

print("=" * 70)
print("  Demo 4: Vector vs Hybrid — Pro, Con, Combined")
print("=" * 70)
print()

# ═══════════════════════════════════════════════════════════════
# RUN 1 — PRO: natural language query, vector nails it
# ═══════════════════════════════════════════════════════════════
print("  ╔══════════════════════════════════════════════════════════════╗")
print("  ║  RUN 1/3 — PRO: natural language query                      ║")
print("  ║  \"how do I set up DevBuddy?\"                                ║")
print("  ╚══════════════════════════════════════════════════════════════╝")
print()
print("  Vector finds exactly the right document. Clean. Relevant.")
print()

chunks = retrieve("how do I set up DevBuddy?", k=3)
for i, c in enumerate(chunks):
    print(f"  [{i+1}] {c.strip().split(chr(10))[0]}")
print()
print("  ✅ Perfect. Semantic search understands the intent.")
print()

# ═══════════════════════════════════════════════════════════════
# RUN 2 — CON: exact keyword, vector may be weak
# ═══════════════════════════════════════════════════════════════
print("  ╔══════════════════════════════════════════════════════════════╗")
print("  ║  RUN 2/3 — CON: exact error code query                      ║")
print("  ║  \"error 408\"                                                ║")
print("  ╚══════════════════════════════════════════════════════════════╝")
print()
print("  Vector finds documents about errors in general. But does it")
print("  find the SPECIFIC incident with error code 408?")
print()

chunks = retrieve("error 408", k=5)
for i, c in enumerate(chunks):
    has = "408" in c
    print(f"  [{i+1}] {'408' if has else '   '}  {c.strip().split(chr(10))[0]}")

print()
print("  Vector returns general error documents. An exact keyword")
print("  like '408' has no semantic meaning — it's just a number.")
print()

# ═══════════════════════════════════════════════════════════════
# RUN 3 — COMBINED: same query, both retrievers
# ═══════════════════════════════════════════════════════════════
print("  ╔══════════════════════════════════════════════════════════════╗")
print("  ║  RUN 3/3 — COMBINED: Vector vs Hybrid on \"error 408\"        ║")
print("  ╚══════════════════════════════════════════════════════════════╝")
print()

vec = retrieve("error 408", k=5)
hyb = hybrid_search("error 408", k=5)

print("  ── Vector only ──")
for i, c in enumerate(vec):
    print(f"  [{i+1}] {c.strip().split(chr(10))[0]}")
print()
print("  ── Hybrid (vector + BM25) ──")
for i, c in enumerate(hyb):
    print(f"  [{i+1}] {c.strip().split(chr(10))[0]}")

print()

diff = set(vec) != set(hyb)
v408 = sum(1 for c in vec if "408" in c)
h408 = sum(1 for c in hyb if "408" in c)

if diff:
    print(f"  ✅ HYBRID FOUND DIFFERENT RESULTS!")
    only_hyb = set(hyb) - set(vec)
    if only_hyb:
        print(f"  Hybrid surfaced {len(only_hyb)} chunk(s) vector missed:")
        for c in only_hyb:
            print(f"     → {c.strip().split(chr(10))[0]}")
elif h408 > v408:
    print(f"  ✅ Hybrid ranked more '408' chunks in top-5 ({h408} vs {v408})")
    print(f"  BM25 is boosting exact keyword matches.")
else:
    print(f"  ══ Top-5 identical ({v408} '408' chunks each).")
    print(f"  With {len(vec)} docs, both retrievers agree at this depth.")
    print(f"  At 50+ docs, BM25 would surface keyword matches that")
    print(f"  vector ignores — error codes have no semantic neighbors.")

print()
print("=" * 70)
print("  Vector = semantic similarity (what does this MEAN?)")
print("  Hybrid = semantic + keyword (what exact WORDS match?)")
print()
print("  Use vector for:   natural language, concepts, intent.")
print("  Use hybrid for:   error codes, ticket IDs, service names,")
print("                    API paths — terms with no semantic meaning.")
print("=" * 70)
