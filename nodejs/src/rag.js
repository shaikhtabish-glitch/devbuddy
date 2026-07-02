/**
 * Week 3 — RAG Pipeline: Embed, Chunk, Store, Retrieve, Ground (Node.js)
 *
 * Uses @xenova/transformers (all-MiniLM-L6-v2) for embeddings — local, free, no API cost.
 * Qdrant for vector storage — runs in Docker, cross-language.
 * Hybrid search with BM25 + vector for exact keyword matching.
 *
 * Imports: import { getLlm } from "./llm.js"
 */
import { readFileSync, readdirSync } from "fs";
import { resolve, extname, dirname } from "path";
import { fileURLToPath } from "url";
import { pipeline } from "@huggingface/transformers";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";
import { QdrantVectorStore } from "@langchain/qdrant";
import { Document } from "@langchain/core/documents";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { getLlm } from "./llm.js";

// ─── Config ───────────────────────────────────────────────────
// ─── Custom Embeddings (no @langchain/community dependency) ─

/**
 * Wraps @huggingface/transformers (Xenova/all-MiniLM-L6-v2) as an
 * embeddings provider compatible with LangChain's QdrantVectorStore.
 * Implements embedQuery() and embedDocuments().
 */
class LocalEmbeddings {
  constructor(modelName = "Xenova/all-MiniLM-L6-v2") {
    this.modelName = modelName;
    this._extractor = null;
  }

  async _getExtractor() {
    if (!this._extractor) {
      this._extractor = await pipeline("feature-extraction", this.modelName);
    }
    return this._extractor;
  }

  async embedQuery(text) {
    const extractor = await this._getExtractor();
    const result = await extractor(text, {
      pooling: "mean",
      normalize: true,
    });
    return Array.from(result.data);
  }

  async embedDocuments(texts) {
    const extractor = await this._getExtractor();
    const results = [];
    for (const text of texts) {
      const result = await extractor(text, {
        pooling: "mean",
        normalize: true,
      });
      results.push(Array.from(result.data));
    }
    return results;
  }
}

const EMBEDDING_MODEL = "Xenova/all-MiniLM-L6-v2";
const QDRANT_URL = process.env.QDRANT_URL || "http://localhost:6333";
const QDRANT_COLLECTION = "devbuddy-docs";
const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, "..", "..", "shared", "data");

let _embeddings = null;
let _vectorstore = null;
let _documents = null;

// ─── Helpers ──────────────────────────────────────────────────

function _getEmbeddings() {
  if (!_embeddings) {
    _embeddings = new LocalEmbeddings(EMBEDDING_MODEL);
  }
  return _embeddings;
}

function _loadDocuments(directory) {
  /**
   * Load .md and .txt files from a directory into Document objects.
   * Returns an array of { pageContent, metadata }.
   */
  const files = [];
  try {
    const entries = readdirSync(directory);
    for (const entry of entries) {
      const ext = extname(entry).toLowerCase();
      if (ext === ".md" || ext === ".txt") {
        const filePath = resolve(directory, entry);
        const content = readFileSync(filePath, "utf-8");
        files.push(
          new Document({
            pageContent: content,
            metadata: { source: entry },
          })
        );
      }
    }
  } catch (e) {
    throw new Error(
      `Failed to load documents from ${directory}: ${e.message}`
    );
  }

  if (files.length === 0) {
    throw new Error(`No .md or .txt files found in ${directory}`);
  }
  return files;
}

// ─── Public API ───────────────────────────────────────────────

/**
 * Load .md and .txt files, chunk them, embed them, and store in Qdrant.
 *
 * @param {string|null} [directory] - Path to document directory. Defaults to shared/data/.
 * @param {number} [chunkSize=512] - Max tokens per chunk.
 * @param {number} [chunkOverlap=64] - Overlapping tokens between chunks.
 * @returns {Promise<number>} Number of chunks indexed.
 */
export async function indexDocuments(
  directory = null,
  chunkSize = 512,
  chunkOverlap = 64
) {
  const target = directory || DATA_DIR;
  const docs = _loadDocuments(target);

  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize,
    chunkOverlap,
    separators: ["\n# ", "\n## ", "\n### ", "\n#### ", "\n", " ", ""],
  });

  const chunks = await splitter.splitDocuments(docs);

  const emb = await _getEmbeddings();

  // Connect to Qdrant, recreate collection with fresh vectors
  _vectorstore = await QdrantVectorStore.fromDocuments(chunks, emb, {
    url: QDRANT_URL,
    collectionName: QDRANT_COLLECTION,
  });

  _documents = chunks;
  return chunks.length;
}

/**
 * Retrieve the top-k most relevant chunks for a query.
 *
 * @param {string} query - The search query.
 * @param {number} [k=3] - Number of chunks to return.
 * @returns {Promise<string[]>} List of chunk content strings, most relevant first.
 */
export async function retrieve(query, k = 3) {
  if (!_vectorstore) {
    throw new Error("No index found. Run indexDocuments() first.");
  }
  const results = await _vectorstore.similaritySearch(query, k);
  return results.map((doc) => doc.pageContent);
}

/**
 * Retrieve using BM25 (keyword) + vector (semantic) and merge via RRF.
 *
 * BM25 catches exact names, IDs, error codes. Vector catches meaning.
 * RRF fusion combines both rankings into one result set.
 *
 * @param {string} query - The search query.
 * @param {number} [k=3] - Number of chunks to return after merging.
 * @returns {Promise<string[]>} List of chunk content strings, merged via RRF.
 */
export async function hybridSearch(query, k = 3) {
  if (!_vectorstore || !_documents) {
    throw new Error("No index found. Run indexDocuments() first.");
  }

  // Vector results
  const vecResults = await _vectorstore.similaritySearch(query, k * 2);
  const vecChunks = vecResults.map((doc) => doc.pageContent);

  // BM25: simple keyword-based retrieval on the loaded documents
  const bm25Chunks = _bm25Search(query, _documents, k * 2);

  // Reciprocal Rank Fusion
  const rrfScores = {};
  const K = 60;

  vecChunks.forEach((chunk, i) => {
    const rank = i + 1;
    rrfScores[chunk] = (rrfScores[chunk] || 0) + 1.0 / (K + rank);
  });
  bm25Chunks.forEach((chunk, i) => {
    const rank = i + 1;
    rrfScores[chunk] = (rrfScores[chunk] || 0) + 1.0 / (K + rank);
  });

  const sorted = Object.entries(rrfScores).sort((a, b) => b[1] - a[1]);
  return sorted.slice(0, k).map(([chunk]) => chunk);
}

/**
 * Simple BM25-inspired keyword search.
 * Scores documents by term frequency of query words.
 */
function _bm25Search(query, documents, k) {
  const queryTerms = query.toLowerCase().split(/\s+/);
  const scored = documents.map((doc) => {
    const text = doc.pageContent.toLowerCase();
    let score = 0;
    for (const term of queryTerms) {
      // Count occurrences
      const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
      const matches = text.match(regex);
      if (matches) score += matches.length;
    }
    return { text: doc.pageContent, score };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, k).map((s) => s.text);
}

/**
 * Answer a question grounded in the retrieved context.
 *
 * Retrieves top-k chunks, injects them into the prompt, and asks the LLM
 * to answer strictly from the provided context.
 *
 * @param {string} query - The user's question.
 * @param {number} [k=3] - Number of chunks to retrieve.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @param {number} [maxTokens=500] - Max tokens in LLM response.
 * @returns {Promise<string>} The LLM's answer, grounded in retrieved documents.
 */
export async function groundedAnswer(query, k = 3, temperature = 0.0, maxTokens = 500) {
  const chunks = await retrieve(query, k);
  const context = chunks.join("\n\n---\n\n");

  const llm = getLlm({ temperature, maxTokens });
  const response = await llm.invoke([
    new SystemMessage(
      "You are a knowledge base assistant. Answer the user's question " +
        "using ONLY the provided context below. If the context does not " +
        "contain the answer, say 'I don't have information about that in " +
        "my knowledge base.' Never invent information.\n\n" +
        "CONTEXT:\n" +
        context
    ),
    new HumanMessage(query),
  ]);

  return response.content.trim();
}

/**
 * Same as groundedAnswer, but also returns the retrieved chunks
 * for transparency — engineers can verify the grounding.
 *
 * @param {string} query - The user's question.
 * @param {number} [k=3] - Number of chunks to retrieve.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @param {number} [maxTokens=500] - Max tokens in LLM response.
 * @returns {Promise<[string, string[]]>} Tuple of [answer, list_of_retrieved_chunks].
 */
export async function groundedAnswerWithChunks(
  query,
  k = 3,
  temperature = 0.0,
  maxTokens = 500
) {
  const chunks = await retrieve(query, k);
  const context = chunks.join("\n\n---\n\n");

  const llm = getLlm({ temperature, maxTokens });
  const response = await llm.invoke([
    new SystemMessage(
      "You are a knowledge base assistant. Answer the user's question " +
        "using ONLY the provided context below. If the context does not " +
        "contain the answer, say 'I don't have information about that in " +
        "my knowledge base.' Never invent information.\n\n" +
        "CONTEXT:\n" +
        context
    ),
    new HumanMessage(query),
  ]);

  return [response.content.trim(), chunks];
}
