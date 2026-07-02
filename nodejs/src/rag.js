// Week 3 — RAG pipeline: embed, chunk, store, retrieve, ground
//
// This file will contain:
// - Document loader (read files from shared/data/)
// - Text chunker (configurable chunk size)
// - Vector store (ChromaDB — local, zero API cost)
// - Retriever (semantic search)
// - Grounded answer function (retrieve → inject → answer)
//
// Imports: import { getLlm } from "./llm.js"
//
// By the end of Week 3, this file will answer questions grounded in your docs.
