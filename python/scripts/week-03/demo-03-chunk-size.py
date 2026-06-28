"""
Demo 3: Chunking — compare retrieval quality across chunk sizes

Indexes the doc set at 256, 512, and 1024 tokens.
Queries the same question at each size and shows the top chunks
with clear visual demarcation between runs.

Run: python scripts/week-03/demo-03-chunk-size.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve

question = "How do I set up DevBuddy?"
runs = [
    (256, "Small  — tight, focused. May split context across chunks."),
    (512, "Medium — sweet spot. Balance of context and relevance."),
    (1024, "Large  — broad, inclusive. May include irrelevant content."),
]

print("=" * 70)
print("  Demo 3: Chunk Size — Same Question, Different Retrieval")
print("=" * 70)
print()
print(f"  QUESTION: {question}")
print()

# ═══════════════════════════════════════════════════════════════
# Three runs — one per chunk size
# ═══════════════════════════════════════════════════════════════
summary = []

for idx, (size, description) in enumerate(runs, 1):
    count = index_documents(chunk_size=size, chunk_overlap=64)
    chunks = retrieve(question, k=3)
    avg_len = sum(len(c) for c in chunks) // len(chunks) if chunks else 0

    summary.append((size, count, avg_len))

    print(f"  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  RUN {idx}/3 — chunk_size = {size:<4}  ({count} chunks indexed)        ║")
    print(f"  ║  {description:<58} ║")
    print(f"  ╠══════════════════════════════════════════════════════════════╣")
    print(f"  ║  Top 3 retrieved chunks (avg {avg_len} chars each):            ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print()

    for i, chunk in enumerate(chunks):
        print(f"  ── Chunk {i+1} ({len(chunk)} chars) ──")
        print(f"  {chunk}")
        print()

    print()

# ═══════════════════════════════════════════════════════════════
# Summary table
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("  SUMMARY")
print("=" * 70)
print()
print(f"  {'Chunk Size':<12} {'Total Chunks':<14} {'Avg Chunk Len':<15}")
print(f"  {'─'*12} {'─'*14} {'─'*15}")
for size, count, avg_len in summary:
    print(f"  {size:<12} {count:<14} {avg_len:<15}")
print()
print("  Observations:")
print("    256  → many small chunks. May split a sentence mid-thought.")
print("    1024 → few large chunks. Payment API content bleeds into")
print("           DevBuddy setup questions (irrelevant noise).")
print("    512  → balanced. Enough context per chunk, minimal noise.")
print()
print("  Rule of thumb: start at 512, then tune based on your")
print("  document structure. Dense specs → smaller chunks (256).")
print("  Narrative docs → larger chunks (1024).")
print("=" * 70)
