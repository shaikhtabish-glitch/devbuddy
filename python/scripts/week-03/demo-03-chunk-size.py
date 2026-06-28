"""
Demo 3: Chunking — compare retrieval quality across chunk sizes

Indexes the doc set at 256, 512, and 1024 tokens.
Queries the same question at each size and shows the top chunks.

Run: python scripts/week-03/demo-03-chunk-size.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag import index_documents, retrieve

question = "How do I set up DevBuddy?"

print("=" * 65)
print("  Demo 3: Chunk Size — Same Question, Different Retrieval")
print("=" * 65)
print()
print(f"  Question: {question}")
print()

for size in [256, 512, 1024]:
    count = index_documents(chunk_size=size, chunk_overlap=64)
    chunks = retrieve(question, k=3)
    print(f"  chunk_size={size} ({count} chunks indexed):")
    for i, chunk in enumerate(chunks):
        print(f"    [{i+1}] ({len(chunk)} chars)")
        print(f"    {chunk}")
        print()
    print()

print("=" * 65)
print("  256: tight, focused. May lose context split across chunks.")
print("  1024: broad, inclusive. May include irrelevant content.")
print("  512:  sweet spot for most doc sets. Start here, then tune.")
print("=" * 65)
