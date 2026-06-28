"""
Demo 4: Hybrid Search — Vector, Keyword, RRF Fusion

Shows how hybrid search combines two retrieval strategies:
  1. Vector search — semantic similarity (understands intent)
  2. Keyword search — exact term matching (catches codes and IDs)
  3. RRF fusion — combines both into a single ranked result

Uses mock data to clearly demonstrate where each approach wins.
This is a teaching tool — the concept is what matters.

Run: python scripts/week-03/demo-04-hybrid-search.py
"""
import re
from typing import List

# ═══════════════════════════════════════════════════════════════
# Document corpus — mirrors shared/data/ content
# ═══════════════════════════════════════════════════════════════

DOCS = {
    "auth-service-spec.md": (
        "# Auth Service — API Specification\n"
        "Endpoints: POST /v1/auth/login, POST /v1/auth/refresh, GET /v1/auth/validate.\n"
        "Error Codes: 401 Invalid token, 403 Insufficient permissions, 429 Rate limit."
    ),
    "CONTRIBUTING.md": (
        "# Contributing to DevBuddy\n"
        "Setup: fork repo, create venv, pip install, copy .env, run verification.py.\n"
        "Code style: Python 3.11+, black, mypy. PRs: one module per PR, approval required."
    ),
    "deploy-log.md": (
        "# Deployment Log — June 2026\n"
        "auth-service v2.0.1 FAILED — token cache invalidation failed. Tracked as INC-799.\n"
        "payment-api v1.8.2 ROLLED BACK — latency spike. Tracked as INC-842."
    ),
    "incident-log.md": (
        "# Production Incidents — June 2026\n"
        "INC-842: payment-api latency spike. Error code 408 (timeout).\n"
        "INC-901: inventory data inconsistency. Tracking PROJ-891, PROJ-892."
    ),
    "inventory-service-sla.md": (
        "# Inventory Service — SLA Status\n"
        "No formal SLA defined. Catalog team has not published uptime guarantees.\n"
        "Contact #catalog-team. Tracked as PROJ-891."
    ),
    "payment-api-spec.md": (
        "# Payment API — Internal Specification\n"
        "Endpoints: POST /v1/payments, GET /v1/payments/{id}, POST /v1/payments/{id}/refund.\n"
        "Error Codes: 402 Insufficient funds, 408 Timeout, 429 Rate limit, 503 Downstream."
    ),
}


class Chunk:
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content

    def __repr__(self):
        return f"[{self.name}] {self.content.strip().splitlines()[0]}"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name


def _make_index() -> List[Chunk]:
    return [Chunk(name, text) for name, text in DOCS.items()]


# ═══════════════════════════════════════════════════════════════
# Mock retrievers — deliberately show different results
# ═══════════════════════════════════════════════════════════════

def mock_vector(query: str, index: List[Chunk]) -> List[Chunk]:
    """
    Simulates semantic search. Good with concepts, weak with exact codes.
    '408' has no semantic meaning — it's just a number. Vector misses it.
    """
    q = query.lower()

    if "set up" in q or "devbuddy" in q:
        # Natural language → vector nails it (setup = CONTRIBUTING.md first)
        names = [
            "CONTRIBUTING.md", "auth-service-spec.md", "inventory-service-sla.md",
            "payment-api-spec.md", "deploy-log.md", "incident-log.md",
        ]
        return [c for n in names for c in index if c.name == n]

    if "error" in q or "408" in q:
        # Exact code → vector finds general error docs, misses the incident
        names = [
            "auth-service-spec.md",      # "Error Codes" section
            "payment-api-spec.md",        # "Error Codes" section
            "deploy-log.md",              # "FAILED" / "ROLLED BACK"
            "incident-log.md",            # has 408 but vector ranks it low
            "inventory-service-sla.md",   # not relevant, filler
            "CONTRIBUTING.md",            # irrelevant
        ]
        return [c for n in names for c in index if c.name == n]

    return index[:3]


def mock_keyword(query: str, index: List[Chunk]) -> List[Chunk]:
    """
    Simulates BM25 keyword matching. Catches exact codes and IDs.
    Weak with natural language — 'set up' matches nothing specific.
    """
    terms = [t.lower() for t in re.findall(r"\w+", query)]
    scored: List[tuple] = []

    for chunk in index:
        score = 0
        for term in terms:
            count = chunk.content.lower().count(term)
            if count:
                score += count * 2  # boost exact keyword hits
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


# ═══════════════════════════════════════════════════════════════
# Reciprocal Rank Fusion — combines both retrievers
# ═══════════════════════════════════════════════════════════════

def rrf_fuse(vec: List[Chunk], key: List[Chunk], k: int = 60) -> List[tuple]:
    """RRF score = sum( 1 / (k + rank) ) for each retriever."""
    scores: dict = {}

    for rank, chunk in enumerate(vec, 1):
        if chunk not in scores:
            scores[chunk] = 0.0
        scores[chunk] += 1.0 / (k + rank)

    for rank, chunk in enumerate(key, 1):
        if chunk not in scores:
            scores[chunk] = 0.0
        scores[chunk] += 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ═══════════════════════════════════════════════════════════════
# Runner — runs one query through all three retrievers
# ═══════════════════════════════════════════════════════════════

def run(query: str, index: List[Chunk]):
    vec = mock_vector(query, index)
    key = mock_keyword(query, index)
    hyb = rrf_fuse(vec, key)

    vec_names = [c.name for c in vec[:3]]
    key_names = [c.name for c in key[:3]]
    hyb_names = [c.name for c, _ in hyb[:3]]

    print(f"  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  QUERY: \"{query}\"")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  ▸ VECTOR ONLY (semantic — understands intent):")
    for i, name in enumerate(vec_names):
        doc = next(c for c in index if c.name == name)
        first = doc.content.strip().splitlines()[0]
        print(f"    [{i+1}] {first}")
    print()
    print(f"  ▸ KEYWORD ONLY (exact match — catches codes and IDs):")
    for i, name in enumerate(key_names):
        doc = next(c for c in index if c.name == name)
        first = doc.content.strip().splitlines()[0]
        print(f"    [{i+1}] {first}")
    print()
    print(f"  ▸ HYBRID (vector + keyword via RRF fusion):")
    for i, (chunk, score) in enumerate(hyb[:3]):
        first = chunk.content.strip().splitlines()[0]
        print(f"    [{i+1}] {score:.4f}  {first}")

    # Show what hybrid adds
    vec_set = set(vec_names)
    hyb_set = set(hyb_names)
    added = hyb_set - vec_set
    if added:
        print(f"\n  ✅ Hybrid added {len(added)} doc(s) vector missed: {', '.join(added)}")
    elif vec_set == hyb_set:
        print(f"\n  ══ All three agree — vector already had the best results.")
    print()


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    index = _make_index()

    print("=" * 70)
    print("  Demo 4: Hybrid Search — Vector, Keyword, RRF Fusion")
    print("=" * 70)
    print()
    print(f"  Corpus: {len(index)} documents (auth spec, API spec, incidents,")
    print(f"          deployments, SLA status, contribution guide)")
    print()

    # PRO: natural language — vector dominates
    print("  ═══════════════════════════════════════════════════════════")
    print("    RUN 1 of 2 — Natural language query")
    print("    Vector finds the right doc by understanding intent.")
    print("  ═══════════════════════════════════════════════════════════")
    run("how do I set up DevBuddy?", index)

    # CON + COMBINED: exact code — keyword fills the gap
    print("  ═══════════════════════════════════════════════════════════")
    print("    RUN 2 of 2 — Exact error code query")
    print("    Vector finds general error docs. Keyword finds the")
    print("    specific incident. Hybrid combines both.")
    print("  ═══════════════════════════════════════════════════════════")
    run("error 408", index)

    print("=" * 70)
    print("  Vector  = what does this MEAN?   (semantic)")
    print("  Keyword = what exact WORDS match? (lexical)")
    print("  Hybrid  = both, fused via RRF     (best of both)")
    print()
    print("  Use hybrid when queries include:")
    print("    • Error codes (408, 401, 503)")
    print("    • Ticket IDs (PROJ-891, INC-842)")
    print("    • Service names (payment-api, auth-service)")
    print("    • Any term with no semantic neighbors")
    print("=" * 70)
