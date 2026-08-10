"""
pipeline.py — ties chunking, embedding, and retrieval together into one
callable RAG tool: given a company and a question, find the most relevant
sections of their most recent filing.

This is what the agent actually calls (it becomes a new entry in Module
2's TOOL_REGISTRY). It hides chunk/embed/index mechanics behind a single
function so the model just asks a question and gets back grounded
evidence — the model never sees FAISS or embeddings directly.
"""
from __future__ import annotations

from app.rag.chunker import chunk_text
from app.rag.embedder import embed_texts
from app.rag.vector_store import ChunkIndex
from app.tools.filings_search import fetch_filing_text, search_filings


def search_filing_content(company: str, question: str, form_type: str = "10-K", top_k: int = 4) -> dict:
    """Find the most relevant filing excerpts for `question` about `company`.

    Pipeline: search EDGAR for the filing -> fetch its text -> chunk it ->
    embed the chunks -> embed the question -> retrieve the top_k closest
    chunks by vector similarity. Returns {"source_url", "excerpts"} on
    success, or {"error": ...} if any step fails — same fail-gracefully
    contract as every other tool in this project.
    """
    filings = search_filings(company, form_type=form_type, limit=1)
    if not filings or "error" in filings[0]:
        return {"error": f"no {form_type} filing found for {company}"}

    filing_url = filings[0]["url"]
    text = fetch_filing_text(filing_url)
    if text.startswith("error:"):
        return {"error": text}

    chunks = chunk_text(text)
    if not chunks:
        return {"error": "filing text was empty after fetching"}

    chunk_embeddings = embed_texts(chunks)
    index = ChunkIndex(chunks, chunk_embeddings)
    query_embedding = embed_texts([question])[0]
    excerpts = index.query(query_embedding, k=top_k)

    return {"source_url": filing_url, "excerpts": excerpts}