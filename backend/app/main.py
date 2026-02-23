import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .ingest import fetch_confluence_pages, build_corpus_and_embeddings
from .faiss_index import FaissIndex
from .embeddings import embed_query
from .llm import generate_answer
from .config import TOP_K


app = FastAPI()

# Allow the React frontend (port 3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory objects
INDEX: Optional[FaissIndex] = None
ALL_CHUNKS = []
METADATAS = []


class AskRequest(BaseModel):
    question: str


class IngestRequest(BaseModel):
    space_key: str


@app.on_event("startup")
async def startup_event():
    """
    Called once when FastAPI server starts
    """
    global INDEX, ALL_CHUNKS, METADATAS

    print("🚀 Server starting...")

    # OPTIONAL: Auto-ingest on startup
    # Commented Confluence ingestion for now; switch to local PDF ingestion.
    # space_key = "ENG"  # example
    # pages = fetch_confluence_pages(space_key)
    from .ingest import load_pdf_pages

    pages = load_pdf_pages()
    ALL_CHUNKS, METADATAS, embeddings = build_corpus_and_embeddings(pages)

    if embeddings:
        dim = len(embeddings[0])
        INDEX = FaissIndex(dim)
        INDEX.add(embeddings, METADATAS)
    else:
        INDEX = None

    print("✅ Confluence data ingested & FAISS index ready")


@app.post("/ingest")
async def ingest(request: IngestRequest):
    """
    Manual ingestion endpoint
    """
    global INDEX, ALL_CHUNKS, METADATAS

    pages = fetch_confluence_pages(request.space_key)
    ALL_CHUNKS, METADATAS, embeddings = build_corpus_and_embeddings(pages)

    if embeddings:
        dim = len(embeddings[0])
        INDEX = FaissIndex(dim)
        INDEX.add(embeddings, METADATAS)
    else:
        INDEX = None

    return {"status": "success", "chunks": len(ALL_CHUNKS)}


def _score_chunk_overlap(question: str, chunk: str) -> int:
    """
    Lexical overlap score between question and a chunk.
    Counts how many non-trivial (len>3) question tokens appear in the chunk.
    """
    q_tokens = set(re.findall(r"\w+", question.lower()))
    text = chunk.lower()
    return sum(1 for t in q_tokens if len(t) > 3 and t in text)


def _rerank_chunks_by_question_overlap(question: str, chunks):
    """
    Simple lexical reranker: prefer chunks that share words with the question.
    This helps ensure queries like 'Confluence access' or 'GitHub access'
    surface the right text.
    """
    return sorted(
        chunks,
        key=lambda c: _score_chunk_overlap(question, c),
        reverse=True,
    )


@app.post("/ask")
async def ask(request: AskRequest):
    """
    Main chat endpoint
    """
    if INDEX is None:
        raise HTTPException(status_code=500, detail="Index not initialized")

    question = request.question

    # First, try to find strong lexical matches anywhere in the corpus.
    # This guarantees that if the PDF explicitly mentions something like
    # "GitHub Access", "Vault Access", etc., we surface those chunks even
    # if the vector search doesn't.
    if ALL_CHUNKS:
        lexically_sorted = _rerank_chunks_by_question_overlap(question, ALL_CHUNKS)
        top_score = _score_chunk_overlap(question, lexically_sorted[0])
        if top_score > 0:
            relevant_chunks = lexically_sorted[: TOP_K * 2]
        else:
            # Fall back to vector search + rerank if no lexical hits.
            query_embedding = embed_query(question)
            search_results = INDEX.search(query_embedding, TOP_K * 3)
            candidate_chunks = [
                ALL_CHUNKS[meta["chunk_index"]] for meta, score in search_results
            ]
            relevant_chunks = _rerank_chunks_by_question_overlap(
                question, candidate_chunks
            )[: TOP_K * 2]
    else:
        relevant_chunks = []

    if not relevant_chunks:
        return {
            "answer": "I can only answer onboarding and team-related questions."
        }

    answer = generate_answer(question, relevant_chunks)

    return {"answer": answer}

