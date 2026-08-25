"""
Week 3 — RAG Pipeline: Embed, Chunk, Store, Retrieve, Ground

Uses sentence-transformers (all-MiniLM-L6-v2) for embeddings — local, free, no API cost.
Qdrant for vector storage — runs in Docker, production-grade, cross-language.
Hybrid search with BM25 + vector for exact keyword matching.

Imports: from src.llm import get_llm
"""
import os
from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_community.retrievers import BM25Retriever
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.llm import get_llm

# ─── Config ───────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = "devbuddy-docs"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "data")

# The system prompt is the guardrail: it constrains the model to the
# retrieved context and tells it to decline out-of-corpus questions.
SYSTEM_PROMPT = (
    "You are a knowledge base assistant. Answer the user's question "
    "using ONLY the provided context below. If the context does not "
    "contain the answer, say 'I don't have information about that in "
    "my knowledge base.' Never invent information.\n\n"
    "CONTEXT:\n"
    "{context}"
)

# The SAME prompt with the guardrail removed — used to show what happens
# without it (the model is no longer told to decline).
NO_GUARDRAIL_PROMPT = (
    "You are a knowledge base assistant. Answer the user's question "
    "using the provided context below.\n\n"
    "CONTEXT:\n"
    "{context}"
)


@dataclass
class RetrievedChunk:
    """A retrieved chunk together with its source document (provenance)."""

    content: str
    source: str


@dataclass
class HybridResult:
    """A hybrid-search hit with its per-retriever ranks — makes RRF visible.

    vec_rank / bm25_rank are 1-based ranks in each retriever's candidate
    list (top k*2); None means that retriever never ranked the chunk (a
    blind spot). rrf_score is the fused score, the sum of 1/(60 + rank)
    over both lists.
    """

    content: str
    source: str
    vec_rank: int | None
    bm25_rank: int | None
    rrf_score: float


_embeddings: HuggingFaceEmbeddings | None = None
_vectorstore: QdrantVectorStore | None = None
_documents: list | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy-load the embedding model (downloaded once on first use)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


def embed_text(text: str) -> list[float]:
    """Embed a single piece of text into a vector (for inspection / demos)."""
    return _get_embeddings().embed_query(text)


def index_documents(
    directory: str | None = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> int:
    """
    Load .md and .txt files from a directory, chunk them, embed them,
    and store in Qdrant.

    Args:
        directory: Path to document directory. Defaults to shared/data/.
        chunk_size: Max tokens per chunk.
        chunk_overlap: Overlapping tokens between chunks.

    Returns:
        Number of chunks indexed.
    """
    global _vectorstore, _documents

    target = directory or DATA_DIR

    loader = DirectoryLoader(
        target,
        glob="**/*.md",
        loader_cls=TextLoader,
        show_progress=False,
    )
    txt_loader = DirectoryLoader(
        target,
        glob="**/*.txt",
        loader_cls=TextLoader,
        show_progress=False,
    )
    docs = loader.load() + txt_loader.load()
    if not docs:
        raise FileNotFoundError(f"No .md or .txt files found in {target}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n# ", "\n## ", "\n### ", "\n#### ", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    emb = _get_embeddings()

    # Connect to Qdrant, recreate collection with fresh vectors
    client = QdrantClient(url=QDRANT_URL)
    try:
        client.delete_collection(QDRANT_COLLECTION)
    except Exception:
        pass

    # Get embedding dimension from the model
    test_vec = emb.embed_query("test")
    vector_size = len(test_vec)

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )

    _vectorstore = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION,
        embedding=emb,
    )
    _vectorstore.add_documents(chunks)
    _documents = chunks
    return len(chunks)


def retrieve(query: str, k: int = 3) -> list[str]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Args:
        query: The search query.
        k: Number of chunks to return.

    Returns:
        List of chunk content strings, most relevant first.
    """
    if _vectorstore is None:
        raise RuntimeError("No index found. Run index_documents() first.")
    results = _vectorstore.similarity_search(query, k=k)
    return [doc.page_content for doc in results]


def retrieve_with_sources(query: str, k: int = 3) -> list[RetrievedChunk]:
    """
    Retrieve the top-k chunks together with their source document names.

    Args:
        query: The search query.
        k: Number of chunks to return.

    Returns:
        List of RetrievedChunk (content + source), most relevant first.
    """
    if _vectorstore is None:
        raise RuntimeError("No index found. Run index_documents() first.")
    results = _vectorstore.similarity_search(query, k=k)
    return [
        RetrievedChunk(
            content=doc.page_content,
            source=os.path.basename(doc.metadata.get("source", "unknown")),
        )
        for doc in results
    ]


def hybrid_search(query: str, k: int = 3) -> list[str]:
    """
    Retrieve using BM25 (keyword) + vector (semantic) and merge via RRF.

    BM25 catches exact names, IDs, error codes. Vector catches meaning.
    RRF fusion combines both rankings into one result set.

    Args:
        query: The search query.
        k: Number of chunks to return after merging.

    Returns:
        List of chunk content strings, merged via reciprocal rank fusion.
    """
    return [r.content for r in hybrid_search_with_scores(query, k=k)]


def hybrid_search_with_scores(query: str, k: int = 3) -> list[HybridResult]:
    """
    hybrid_search() plus the internals: for every final hit, report its
    rank in EACH retriever (None = that retriever never ranked it) and
    the fused RRF score.

    RRF (reciprocal rank fusion): score = sum over retrievers of
    1 / (60 + rank). A chunk ranked #1 by BM25 and #7 by vector scores
    1/61 + 1/67 — which is why exact-ID matches jump to the top.

    Args:
        query: The search query.
        k: Number of chunks to return after merging.

    Returns:
        List of HybridResult (content + source + per-retriever ranks),
        in fused order.
    """
    if _vectorstore is None or _documents is None:
        raise RuntimeError("No index found. Run index_documents() first.")

    # Per-retriever candidate lists (top k*2 each). A chunk that one side
    # misses entirely is a "blind spot" — reported as a None rank.
    vec_chunks = [
        d.page_content for d in _vectorstore.similarity_search(query, k=k * 2)
    ]
    bm25 = BM25Retriever.from_documents(_documents, k=k * 2)
    bm25_chunks = [d.page_content for d in bm25.invoke(query)]

    sources = {
        d.page_content: os.path.basename(d.metadata.get("source", "unknown"))
        for d in _documents
    }

    K = 60  # RRF constant: damps rank contributions; no tuning needed
    rrf_scores: dict[str, float] = {}

    for rank, chunk in enumerate(vec_chunks, 1):
        rrf_scores[chunk] = rrf_scores.get(chunk, 0.0) + 1.0 / (K + rank)

    for rank, chunk in enumerate(bm25_chunks, 1):
        rrf_scores[chunk] = rrf_scores.get(chunk, 0.0) + 1.0 / (K + rank)

    return [
        HybridResult(
            content=chunk,
            source=sources.get(chunk, "unknown"),
            vec_rank=vec_chunks.index(chunk) + 1 if chunk in vec_chunks else None,
            bm25_rank=bm25_chunks.index(chunk) + 1 if chunk in bm25_chunks else None,
            rrf_score=score,
        )
        for chunk, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:k]
    ]


def answer_with_context(
    query: str,
    chunks: list[str],
    system_prompt: str = SYSTEM_PROMPT,
    temperature: float = 0.0,
) -> str:
    """
    The "augment + generate" step: inject ALREADY-RETRIEVED chunks into a
    system prompt and ask the LLM to answer. The system prompt is the
    guardrail — pass SYSTEM_PROMPT to ground, or NO_GUARDRAIL_PROMPT to see
    what the model does without it.

    Kept separate from retrieval so callers can inspect (and display) the
    exact chunks that ground the answer before sending them to the model.

    Args:
        query: The user's question.
        chunks: Pre-retrieved chunk contents (from retrieve / hybrid_search).
        system_prompt: The prompt template (must contain a {context} slot).
        temperature: 0.0 for deterministic output.

    Returns:
        The LLM's answer.
    """
    context = "\n\n---\n\n".join(chunks)
    llm = get_llm(temperature=temperature)
    response = llm.invoke([
        SystemMessage(content=system_prompt.format(context=context)),
        HumanMessage(content=query),
    ])
    return response.content.strip()


def grounded_answer_from_chunks(
    query: str, chunks: list[str], temperature: float = 0.0
) -> str:
    """Ground an answer using SYSTEM_PROMPT (the guardrail). See answer_with_context."""
    return answer_with_context(query, chunks, SYSTEM_PROMPT, temperature)


def grounded_answer(query: str, k: int = 3, temperature: float = 0.0) -> str:
    """
    Answer a question grounded in the retrieved context.

    Retrieves top-k chunks, injects them into the prompt, and asks the LLM
    to answer strictly from the provided context.

    Args:
        query: The user's question.
        k: Number of chunks to retrieve.
        temperature: 0.0 for deterministic output.

    Returns:
        The LLM's answer, grounded in retrieved documents.
    """
    chunks = retrieve(query, k=k)
    return grounded_answer_from_chunks(query, chunks, temperature)


def grounded_answer_with_chunks(
    query: str, k: int = 3, temperature: float = 0.0
) -> tuple[str, list[str]]:
    """
    Same as grounded_answer, but also returns the retrieved chunks
    for transparency — engineers can verify the grounding.

    Args:
        query: The user's question.
        k: Number of chunks to retrieve.
        temperature: 0.0 for deterministic output.

    Returns:
        Tuple of (answer, list_of_retrieved_chunks).
    """
    chunks = retrieve(query, k=k)
    return grounded_answer_from_chunks(query, chunks, temperature), chunks
