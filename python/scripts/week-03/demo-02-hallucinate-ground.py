"""
Demo 2: Hallucinate → Ground

The system prompt is the guardrail. This demo proves it by holding the
question AND the retrieved chunks fixed, and changing only the system prompt:

  1. OUT-OF-CORPUS + guardrail   → the model declines
  2. OUT-OF-CORPUS, no guardrail → the model hallucinates
  3. IN-CORPUS + guardrail       → the model answers from the chunks

Run: python scripts/week-03/demo-02-hallucinate-ground.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import (
    NO_GUARDRAIL_PROMPT,
    SYSTEM_PROMPT,
    answer_with_context,
    index_documents,
    retrieve_with_sources,
)

OUT_OF_CORPUS = "What's the revenue forecast for Q4 2028?"
IN_CORPUS = "How do I contribute code to DevBuddy?"
K = 3
BORDER = "=" * 72

print(BORDER)
print("  Demo 2: Hallucinate → Ground")
print(BORDER)
print()

index_documents(chunk_size=512, chunk_overlap=64)
print("  ✅ Index ready")
print()

# ── The out-of-corpus retrieval ───────────────────────────────
# WHY does the retriever return "random" info for an out-of-corpus
# question ("Q4 2028 revenue") instead of nothing?
#
# Because vector search is a top-k nearest-neighbour query: it ALWAYS
# returns k chunks and has no "not found" concept and no relevance
# cutoff. For this question the query vector points into an empty
# region of vector space, so the "nearest" chunks are still far away
# (scores ~0.30 / 0.27 / 0.22, vs ~0.60 for an in-corpus question)
# and happen to be about payments, incidents and SLAs.
#
# Similarity is a RELATIVE ranking, not an ABSOLUTE relevance
# judgement: Qdrant sorts everything by distance and hands back the
# top-k. It never says "0.22 is too low to be useful — nothing
# matched". That decision is left to the guardrail below.
print(f'  Out-of-corpus question: "{OUT_OF_CORPUS}"')
print()
print(f"  The retriever always returns its top-{K} chunks — even when none")
print("  of them answer the question:")
print()
chunks = retrieve_with_sources(OUT_OF_CORPUS, k=K)
for i, c in enumerate(chunks, 1):
    print(f"  [{i}] {c.source}")
    print(f"      {c.content}")
    print()
print('  None of these mention Q4 2028 revenue. Retrieval can\'t return')
print('  "nothing" — it returns its best (irrelevant) guess.')
print()

# ── With the guardrail ────────────────────────────────────────
print("  ── With the guardrail ───────────────────────────────────")
print()
print("  The system prompt tells the model to decline when the context")
print("  doesn't contain the answer:")
print()
for line in SYSTEM_PROMPT.format(context=f"<the {K} chunks above>").splitlines():
    print(f"  │ {line}")
print()
guarded = answer_with_context(OUT_OF_CORPUS, [c.content for c in chunks], SYSTEM_PROMPT)
print(f"  Answer: {guarded}")
print()

# ── Without the guardrail ─────────────────────────────────────
print("  ── Without the guardrail ────────────────────────────────")
print()
print("  Same question, same chunks — but the decline instruction is gone:")
print()
for line in NO_GUARDRAIL_PROMPT.format(context=f"<the {K} chunks above>").splitlines():
    print(f"  │ {line}")
print()
unguarded = answer_with_context(OUT_OF_CORPUS, [c.content for c in chunks], NO_GUARDRAIL_PROMPT)
print(f"  Answer: {unguarded}")
print()

# ── In-corpus ─────────────────────────────────────────────────
print("  ── In-corpus (grounded) ─────────────────────────────────")
print()
print(f'  Question: "{IN_CORPUS}"')
print()
grounded_chunks = retrieve_with_sources(IN_CORPUS, k=K)
for i, c in enumerate(grounded_chunks, 1):
    print(f"  [{i}] {c.source}")
    print(f"      {c.content}")
    print()
grounded = answer_with_context(IN_CORPUS, [c.content for c in grounded_chunks], SYSTEM_PROMPT)
print(f"  Answer: {grounded}")
print()

print(BORDER)
print("  Same retriever. Same chunks. Only the system prompt changed.")
print("  The guardrail is what separates a hallucination from a refusal.")
print(BORDER)
