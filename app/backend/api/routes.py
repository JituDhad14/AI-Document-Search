# app/backend/api/routes.py

from collections import Counter
from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException, Body
import os
import numpy as np
from pydantic import BaseModel
from typing import List, Dict, Any

from app.backend.ingestion.text_splitter import split_text
from app.backend.ingestion.embedder import get_model
from app.backend.vectorstore.faiss_index import FaissIndexer
from app.backend.retrieval.rag_pipeline import run_rag, call_llm
from app.backend.config import FAISS_INDEX_PATH
from app.backend.ingestion.pdf_loader import load_pdf  # make sure you have this function
from fastapi import status
from pathlib import Path
from fastapi import BackgroundTasks
from pathlib import Path

router = APIRouter()

# Global FAISS indexer reference (lazy-loaded / reused)
INDEXER: FaissIndexer | None = None


def get_indexer() -> FaissIndexer | None:
    """
    Lazy load FAISS indexer from disk if not already loaded.

    On a fresh run with no index file, this will return None and
    the endpoints will respond with a 404 until at least one upload happens.
    """
    global INDEXER
    if INDEXER is None and os.path.exists(FAISS_INDEX_PATH):
        model = get_model()
        try:
            dim = model.get_sentence_embedding_dimension()
        except Exception:
            emb = model.encode(["hello"])
            dim = np.asarray(emb).shape[-1]

        INDEXER = FaissIndexer(dim=int(dim), index_path=str(FAISS_INDEX_PATH))

    return INDEXER
# at top of file (if not present), define where raw files are stored

# ensure DATA_RAW is set to the folder where you save files
DATA_RAW = Path("app/data/raw")

# Replace or add this handler in backend/api/routes.py
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, background_tasks: BackgroundTasks):
    """
    Fast delete: remove file immediately and schedule FAISS cleanup in background.
    Returns quickly so client does not block waiting for index rebuild.
    """
    global INDEXER

    safe_name = Path(doc_id).name
    file_path = DATA_RAW / safe_name

    # 1) Remove file from disk (fast)
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file on disk: {e}")

    # 2) Schedule index cleanup as a background task
    def _cleanup(name: str):
        try:
            if INDEXER is not None and hasattr(INDEXER, "delete_by_source"):
                print(f"[background] Starting FAISS cleanup for {name}")
                removed = INDEXER.delete_by_source(name)
                INDEXER.save()
                print(f"[background] FAISS cleanup done for {name}, removed {removed} chunks")
            else:
                print("[background] INDEXER or delete_by_source not available - index may be stale")
        except Exception as exc:
            # Log exception but do not raise (background)
            print(f"[background] FAISS cleanup failed for {name}: {exc}")

    background_tasks.add_task(_cleanup, safe_name)

    # 3) Return quickly
    return {"status": "accepted", "deleted": safe_name}


# -----------------------------
# Post-process options config
# -----------------------------
# Keys and friendly labels + small template headers for the LLM prompts.
POSTPROCESS_OPTIONS = {
    "quick_summary": {
        "label": "Quick summary",
        "template": lambda title: (
            "You are a helpful summarization assistant. Produce a short concise summary (3-5 sentences) "
            f"of the document titled: {title}. Focus on the main idea and the most important conclusions.\n\nContext:\n"
        ),
    },
    "key_points": {
        "label": "Key points",
        "template": lambda title: (
            "You are an assistant that extracts the most important takeaways. Provide an ordered list of the "
            f"top 8–12 key points from the document titled: {title}.\n\nContext:\n"
        ),
    },
    "outline": {
        "label": "Structured outline (TOC)",
        "template": lambda title: (
            "You are an assistant that builds an outline or table of contents from document chunks. Produce a "
            f"hierarchical outline with short headings and indicate page numbers where available for the document: {title}.\n\nContext:\n"
        ),
    },
    "entities": {
        "label": "Important entities & facts",
        "template": lambda title: (
            "Extract named entities, important facts, numbers, dates, metrics, and definitions from the document titled: "
            f"{title}. Present them as short labeled bullets grouped by type (People, Organizations, Dates, Numbers, Terms).\n\nContext:\n"
        ),
    },
    "faqs": {
        "label": "Auto-generated FAQs",
        "template": lambda title: (
            "Create 6 concise FAQ pairs (question + short answer) that a reader would ask after reading the document titled: "
            f"{title}. Use the provided context to answer.\n\nContext:\n"
        ),
    },
}


def build_option_prompt(option_key: str, doc_title: str, contexts: List[dict]) -> str:
    """
    Build a prompt for a post-processing option.
    - option_key: one of POSTPROCESS_OPTIONS keys
    - doc_title: filename or friendly title
    - contexts: list of metadata dicts (each should have 'source', 'text', optionally 'page')
    """
    if option_key not in POSTPROCESS_OPTIONS:
        raise ValueError("Invalid option key")

    header = POSTPROCESS_OPTIONS[option_key]["template"](doc_title)
    ctx_text = ""
    # Attach up to a reasonable amount of context; truncate each chunk to avoid huge prompts
    for c in contexts:
        src = c.get("source", "unknown")
        page = c.get("page")
        snippet = (c.get("text", "") or "")[:800]  # keep first 800 chars per chunk
        if page:
            ctx_text += f"Source: {src} (page {page})\n{snippet}\n\n"
        else:
            ctx_text += f"Source: {src}\n{snippet}\n\n"

    footer = (
        "\nRespond concisely. Use bullet lists when appropriate. If the requested information is not present in the context, say 'Not found in the document.'"
    )
    return header + ctx_text + footer


# ===========================
# Upload PDF endpoint
# ===========================
@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a single PDF, extract text, split to chunks, embed and add to FAISS index.

    - Reuses a global INDEXER instance (does not wipe previous docs).
    - Saves index to disk at FAISS_INDEX_PATH.
    - Returns post-processing options and a local file URL for immediate use.
    """
    global INDEXER
    filename = file.filename

    try:
        # 1. Load and split text
        # load_pdf should accept a file-like object (UploadFile.file)
        text = load_pdf(file.file)
        chunks = split_text(text)

        if not chunks:
            raise ValueError("No text could be extracted from the uploaded PDF.")

        # 2. Get embedding model and dimension
        model = get_model()
        try:
            dim = model.get_sentence_embedding_dimension()
        except Exception:
            emb = model.encode([chunks[0]])
            dim = np.asarray(emb).shape[-1]

        embeddings = model.encode(chunks, show_progress_bar=False)
        vectors = np.asarray(embeddings, dtype="float32")

        # 3. Init or reuse FAISS index
        if INDEXER is None:
            INDEXER = FaissIndexer(dim=int(dim), index_path=str(FAISS_INDEX_PATH))

        # 4. Prepare metadata and add to index
        metas = [{"source": filename, "text": c} for c in chunks]

        INDEXER.add(vectors, metas)
        INDEXER.save()

        # IMPORTANT: local file url for now (you requested to use local path)
        # Replace/transform this later if you serve PDFs over HTTP.
        file_url = f"file:///C:/Desktop/ai-pdf-chatbot/app/data/raw/{filename}"

        # Build postprocess options list to return to frontend
        options = [{"key": k, "label": v["label"]} for k, v in POSTPROCESS_OPTIONS.items()]

        return {
            "status": "ok",
            "filename": filename,
            "chunks_added": len(chunks),
            "file_url": file_url,
            "postprocess_options": options,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ===========================
# Search endpoint (RAG)
# ===========================
@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    k: int = Query(5, ge=1),
    indexer: FaissIndexer | None = Depends(get_indexer),
):
    """
    GET /search?q=...&k=5

    Runs the RAG pipeline and returns the full result
    (query, answer, sources) or an error.
    """
    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(
            status_code=404,
            detail="No index available. Upload documents first.",
        )

    try:
        result = run_rag(q, indexer, k=k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ===========================
# Chat endpoint (RAG)
# ===========================
class ChatQuery(BaseModel):
    query: str
    k: int = 5  # number of chunks to retrieve


@router.post("/chat")
async def chat(
    body: ChatQuery,
    indexer: FaissIndexer | None = Depends(get_indexer),
):
    """
    POST /chat

    Body:
        {
          "query": "your question",
          "k": 5
        }

    Returns:
        {
          "query": str,
          "answer": str,
          "sources": [str, ...]
        }
    """
    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(
            status_code=404,
            detail="No index available. Upload documents first.",
        )

    try:
        result = run_rag(body.query, indexer, k=body.k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ===========================
# Documents list endpoint
# ===========================
@router.get("/docs")
async def list_docs(indexer: FaissIndexer | None = Depends(get_indexer)):
    """
    GET /docs

    Returns a simple list of documents inferred from the FAISS metadata.

    Response:
        {
          "documents": [
            {"id": "file1.pdf", "name": "file1.pdf", "chunks": 42},
            ...
          ]
        }
    """
    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(
            status_code=404,
            detail="No index available. Upload documents first.",
        )

    sources = [m.get("source", "unknown") for m in indexer.meta]
    counts = Counter(sources)

    docs = [
        {"id": name, "name": name, "chunks": counts[name]}
        for name in counts
    ]

    return {"documents": docs}


# ===========================
# Processing endpoint (post-upload actions)
# ===========================
class ProcessRequest(BaseModel):
    filename: str
    option: str
    k: int = 5


@router.post("/process")
async def process_document(body: ProcessRequest, indexer: FaissIndexer | None = Depends(get_indexer)):
    """
    POST /process
    Body:
      { "filename": "DataMining-Unit-1.pdf", "option": "key_points", "k": 5 }

    Returns:
      {
        "status": "ok",
        "filename": "...",
        "option": "...",
        "label": "...",
        "result": "<LLM output>",
        "sources": [ ["DataMining-Unit-1.pdf", 3], ... ]
      }
    """
    if body.option not in POSTPROCESS_OPTIONS:
        raise HTTPException(status_code=400, detail="Invalid processing option")

    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(status_code=404, detail="No index available. Upload documents first.")

    # Retrieve contexts (pull more than k to allow filename filtering)
    try:
        raw_contexts = indexer.retrieve(body.filename, k=body.k * 3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

    # Filter contexts to the given filename where possible
    filtered = [c for c in raw_contexts if c.get("source") == body.filename]
    contexts = filtered if len(filtered) > 0 else raw_contexts

    if not contexts:
        return {
            "status": "ok",
            "filename": body.filename,
            "option": body.option,
            "label": POSTPROCESS_OPTIONS[body.option]["label"],
            "result": "No relevant content found in the index for this document.",
            "sources": [],
        }

    # Build the option-specific prompt
    prompt = build_option_prompt(body.option, body.filename, contexts)

    # Call the LLM (uses your existing wrapper)
    try:
        answer = call_llm(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    # Build unique (source, page) pairs for sources
    sources_set = []
    for c in contexts:
        src = c.get("source", "unknown")
        page = c.get("page")
        sources_set.append([src, page] if page else [src, None])

    # Deduplicate while preserving order
    seen = set()
    dedup_sources = []
    for s in sources_set:
        key = (s[0], s[1])
        if key not in seen:
            seen.add(key)
            dedup_sources.append(s)

    return {
        "status": "ok",
        "filename": body.filename,
        "option": body.option,
        "label": POSTPROCESS_OPTIONS[body.option]["label"],
        "result": answer,
        "sources": dedup_sources,
    }
from fastapi import BackgroundTasks
from pathlib import Path

DATA_RAW = Path("app/data/raw")   # adjust if needed

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, background_tasks: BackgroundTasks):
    """
    Delete the file immediately, then clean FAISS in the background.
    UI should not hang.
    """
    global INDEXER

    safe_name = Path(doc_id).name
    file_path = DATA_RAW / safe_name

    # Delete PDF immediately
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    # Background FAISS cleanup
    def cleanup(name: str):
        try:
            if INDEXER and hasattr(INDEXER, "delete_by_source"):
                INDEXER.delete_by_source(name)
                INDEXER.save()
                print(f"Background FAISS cleanup complete for {name}")
            else:
                print("Warning: delete_by_source missing in INDEXER")
        except Exception as exc:
            print("FAISS cleanup failed:", exc)

    background_tasks.add_task(cleanup, safe_name)

    # Respond instantly
    return {"status": "accepted", "deleted": safe_name}
