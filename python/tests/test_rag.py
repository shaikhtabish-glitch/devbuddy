"""Tests for src/rag.py — Week 3"""
import pytest
from src.rag import (
    index_documents, retrieve, hybrid_search,
    grounded_answer, grounded_answer_with_chunks,
)


@pytest.fixture(autouse=True)
def _build_index():
    """Index the doc set fresh before each test."""
    import src.rag as rag
    rag._vectorstore = None
    rag._documents = None
    rag._embeddings = None
    count = index_documents(chunk_size=512, chunk_overlap=64)
    if count == 0:
        # Populated collection → reuse path (no re-embed). It must still
        # leave the module fully usable: store reconnected, BM25 corpus set.
        assert rag._vectorstore is not None, "reuse must reconnect the store"
        assert rag._documents, "reuse must repopulate the BM25 corpus"


def test_rag_imports_llm():
    """rag.py imports from llm.py — the import graph holds.

    Checks the whole delegation CHAIN (grounded_answer →
    grounded_answer_from_chunks → answer_with_context → get_llm),
    not just one function frame — a substring check on a delegating
    function would pass or fail for the wrong reason.
    """
    import inspect
    import src.rag as rag

    assert "from src.llm import get_llm" in inspect.getsource(rag), \
        "rag.py must import the Week 1 provider"

    chain = inspect.getsource(rag.grounded_answer)
    if "grounded_answer_from_chunks" in chain:
        chain += inspect.getsource(rag.grounded_answer_from_chunks)
    if "answer_with_context" in chain and hasattr(rag, "answer_with_context"):
        chain += inspect.getsource(rag.answer_with_context)
    assert "get_llm" in chain, \
        "grounded_answer must reach get_llm through its delegation chain"


def test_index_creates_chunks():
    """Indexing produces chunks — or reconnects to an existing populated
    collection, in which case the module must still be fully usable."""
    import src.rag as rag
    count = index_documents(chunk_size=512)
    if count == 0:
        assert rag._vectorstore is not None
        assert rag._documents, "reuse path must repopulate the BM25 corpus"
        assert retrieve("payment", k=1), "reused collection must retrieve"
    else:
        assert count >= 4, f"Expected at least 4 chunks, got {count}"


def test_retrieve_returns_relevant_chunks():
    """Retrieval finds chunks relevant to the query."""
    chunks = retrieve("What endpoints does the payment API expose?", k=3)
    assert len(chunks) > 0, "No chunks retrieved"
    assert any("payment" in c.lower() for c in chunks), (
        "Retrieved chunks should mention 'payment'"
    )


def test_index_preserves_utf8_punctuation():
    chunks = retrieve("INC-842 payment-api latency spike", k=20)
    assert any("INC-842 — payment-api latency spike" in chunk for chunk in chunks)


def test_retrieve_returns_different_chunks_for_different_queries():
    """Different queries return different chunks."""
    pay_chunks = retrieve("payment API timeout", k=3)
    contrib_chunks = retrieve("how to contribute", k=3)
    assert pay_chunks != contrib_chunks, (
        "Different queries should return different chunks"
    )


def test_grounded_answer_uses_context():
    """The LLM answers from the retrieved context, not training data."""
    answer = grounded_answer("What is the SLA for the payment API?", k=3)
    assert len(answer) > 10, "Answer is too short"
    # Should reference the SLA from the payment API spec
    assert any(
        phrase in answer.lower()
        for phrase in ["99.95", "sla", "uptime"]
    ), f"Answer doesn't reference the payment API SLA: {answer[:100]}"


def test_grounded_answer_with_chunks_returns_both():
    """grounded_answer_with_chunks returns answer + chunks."""
    answer, chunks = grounded_answer_with_chunks(
        "What is the SLA for the payment API?", k=3
    )
    assert len(answer) > 10
    assert len(chunks) > 0
    assert any("99.95" in c or "SLA" in c for c in chunks), (
        "Chunks should contain SLA information"
    )


def test_out_of_corpus_question_says_no_information():
    """An out-of-corpus question should not hallucinate."""
    answer = grounded_answer(
        "What's the revenue forecast for Q4 2028?", k=3
    )
    assert (
        "don't have" in answer.lower()
        or "no information" in answer.lower()
    ), f"Model should decline to answer, got: {answer[:100]}"


def test_hybrid_search_includes_keyword_matches():
    """Hybrid search should return results for keyword queries."""
    hyb = hybrid_search("payment-api", k=3)
    vec = retrieve("payment-api", k=3)
    assert len(hyb) > 0, "Hybrid search returned no results"
    # Hybrid should at minimum match vector quality
    assert len(hyb) == len(vec), (
        f"Hybrid ({len(hyb)}) should return same count as vector ({len(vec)})"
    )


def test_chunk_size_changes_chunk_count():
    """Different chunk sizes produce different numbers of chunks."""
    count_256 = index_documents(chunk_size=256, force=True)
    count_1024 = index_documents(chunk_size=1024, force=True)

    # Smaller chunks = more chunks. Larger chunks = fewer.
    assert count_256 > count_1024, (
        f"Expected chunk_size=256 ({count_256}) to produce more chunks "
        f"than chunk_size=1024 ({count_1024})"
    )
    # Restore default size for subsequent tests
    index_documents(chunk_size=512, force=True)


def test_unindexed_retrieve_raises():
    """retrieve with no usable collection raises a clear error.

    The Week 6 lazy-connect attaches to an EXISTING index — it never
    invents one — so pointing at a collection that doesn't exist must
    still raise 'No index found'.
    """
    import src.rag as rag
    old_vs, old_coll = rag._vectorstore, rag.QDRANT_COLLECTION
    rag._vectorstore = None
    rag.QDRANT_COLLECTION = "no-such-collection"
    try:
        with pytest.raises(RuntimeError, match="No index found"):
            retrieve("test query")
    finally:
        rag._vectorstore = old_vs
        rag.QDRANT_COLLECTION = old_coll
