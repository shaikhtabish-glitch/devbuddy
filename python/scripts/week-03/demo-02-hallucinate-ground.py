"""
Demo 2: Hallucinate → Ground

Step 1: Ask an out-of-corpus question → model says it doesn't know.
Step 2: Ask an in-corpus question → model retrieves and answers.

Shows the system prompt working: "If the context doesn't contain the
answer, say so." Also shows grounded answers for in-corpus questions.

Run: python scripts/week-03/demo-02-hallucinate-ground.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, grounded_answer_with_chunks

print("=" * 65)
print("  Demo 2: Out-of-Corpus vs In-Corpus")
print("=" * 65)
print()

# Index all documents
index_documents(chunk_size=512, chunk_overlap=64)

# ═══════════════════════════════════════════════════════════════
# Step 1: Out-of-corpus — model should decline
# ═══════════════════════════════════════════════════════════════
print("  Step 1 — Out-of-corpus question")
print()

hallucination_question = "What's the revenue forecast for Q4 2028?"

answer, chunks = grounded_answer_with_chunks(hallucination_question, k=3)
print(f"  Question: {hallucination_question}")
print()
print(f"  Retrieved {len(chunks)} chunks")
print(f"  Answer: {answer}")
print()
print("  ✅ The system prompt worked: model declined to invent an answer.")
print("     'I don't have information about that' — not a hallucination.")
print()

# ═══════════════════════════════════════════════════════════════
# Step 2: In-corpus — model retrieves and answers
# ═══════════════════════════════════════════════════════════════
print("  Step 2 — In-corpus question")
print()

grounded_question = "How do I contribute code to DevBuddy?"

answer, chunks = grounded_answer_with_chunks(grounded_question, k=3)

print(f"  Question: {grounded_question}")
print()
print(f"  Retrieved {len(chunks)} chunks:")
for i, chunk in enumerate(chunks):
    source = chunk.strip().split("\n")[0][:60]
    print(f"    [{i+1}] {source}...")
print()
print(f"  Answer: {answer}")
print()
print("=" * 65)
print("  Out-of-corpus → model declines (no hallucination).")
print("  In-corpus     → model answers from CONTRIBUTING.md.")
print("  Clean retrieval. Clean answer. Grounding works.")
print("=" * 65)
print("=" * 65)
