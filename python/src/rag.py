"""
Week 3 — RAG Pipeline: Embed, Chunk, Store, Retrieve, Ground

Uses sentence-transformers (all-MiniLM-L6-v2) for embeddings — local, free, no API cost.
Qdrant for vector storage — runs in Docker, production-grade, cross-language.
Hybrid search with BM25 + vector for exact keyword matching.

Imports: from src.llm import get_llm
"""
import os
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

_embeddings: HuggingFaceEmbeddings | None = None
_vectorstore: QdrantVectorStore | None = None
_documents: list | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy-load the embedding model (downloaded once on first use)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


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
    if _vectorstore is None or _documents is None:
        raise RuntimeError("No index found. Run index_documents() first.")

    # Vector results
    vec_results = _vectorstore.similarity_search(query, k=k * 2)
    vec_chunks = [doc.page_content for doc in vec_results]

    # BM25 results
    bm25 = BM25Retriever.from_documents(_documents, k=k * 2)
    bm25_results = bm25.invoke(query)
    bm25_chunks = [doc.page_content for doc in bm25_results]

    # Reciprocal Rank Fusion
    rrf_scores: dict[str, float] = {}
    K = 60

    for rank, chunk in enumerate(vec_chunks, 1):
        rrf_scores[chunk] = rrf_scores.get(chunk, 0.0) + 1.0 / (K + rank)

    for rank, chunk in enumerate(bm25_chunks, 1):
        rrf_scores[chunk] = rrf_scores.get(chunk, 0.0) + 1.0 / (K + rank)

    sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in sorted_chunks[:k]]


def grounded_answer(query: str, k: int = 3, temperature: float = 0.0) -> str:
    """
    Answer a question grounded in the retrieved context.

    Retrieves top-k chunks, injects them into the prompt, and asks the LLM
    to answer strictly from the provided context. If the context doesn't
    contain the answer, the model is instructed to say so.

    Args:
        query: The user's question.
        k: Number of chunks to retrieve.
        temperature: 0.0 for deterministic output.

    Returns:
        The LLM's answer, grounded in retrieved documents.
    """
    chunks = retrieve(query, k=k)
    context = "\n\n---\n\n".join(chunks)

    llm = get_llm(temperature=temperature)
    response = llm.invoke([
        SystemMessage(content=(
            "You are a knowledge base assistant. Answer the user's question "
            "using ONLY the provided context below. If the context does not "
            "contain the answer, say 'I don't have information about that in "
            "my knowledge base.' Never invent information.\n\n"
            "CONTEXT:\n"
            f"{context}"
        )),
        HumanMessage(content=query),
    ])

    return response.content.strip()


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
    context = "\n\n---\n\n".join(chunks)

    llm = get_llm(temperature=temperature)
    response = llm.invoke([
        SystemMessage(content=(
            "You are a knowledge base assistant. Answer the user's question "
            "using ONLY the provided context below. If the context does not "
            "contain the answer, say 'I don't have information about that in "
            "my knowledge base.' Never invent information.\n\n"
            "CONTEXT:\n"
            f"{context}"
        )),
        HumanMessage(content=query),
    ])

    return response.content.strip(), chunks
