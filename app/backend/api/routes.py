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
from app.backend.config import FAISS_INDEX_PATH, CHUNKS_META_PATH
from app.backend.ingestion.pdf_loader import load_pdf  # make sure you have this function
from fastapi import status
from pathlib import Path
from fastapi import BackgroundTasks
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import Depends
from app.backend.db.database import get_db
from app.backend.db.models import Feedback
from pydantic import BaseModel
class FeedbackRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str



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
from typing import List

@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    global INDEXER

    print("🔥 UPLOAD ENDPOINT CALLED")

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if len(files) > 2:
        raise HTTPException(status_code=400, detail="Maximum 2 documents allowed at once")

    # -----------------------------
    # INIT WORKSPACE IF FIRST UPLOAD
    # -----------------------------
    if INDEXER is None:
        print("🧠 Creating new session workspace")

        DATA_RAW.mkdir(parents=True, exist_ok=True)

        model = get_model()
        dim = model.get_sentence_embedding_dimension()

        INDEXER = FaissIndexer(dim=int(dim), index_path=str(FAISS_INDEX_PATH))
        INDEXER.reset()   # empty clean session

    # -----------------------------
    # WORKSPACE LIMIT CHECK
    # -----------------------------
    existing_docs = set(m["source"] for m in INDEXER.meta)
    incoming_docs = set(file.filename for file in files)

    total_after = existing_docs | incoming_docs

    if len(total_after) > 2:
        raise HTTPException(
            status_code=400,
            detail=f"Workspace already has {len(existing_docs)} document(s). Max allowed = 2."
        )

    total_chunks = 0
    uploaded_docs = []

    model = get_model()

    # -----------------------------
    # INGEST FILES
    # -----------------------------
    for file in files:
        filename = file.filename

        # skip if already uploaded
        if filename in existing_docs:
            continue

        path = DATA_RAW / filename

        with open(path, "wb") as buffer:
            buffer.write(await file.read())

        text = load_pdf(open(path, "rb"))
        chunks = split_text(text)

        if not chunks:
            continue

        embeddings = model.encode(chunks, show_progress_bar=False)
        vectors = np.asarray(embeddings, dtype="float32")

        metas = [{"source": filename, "text": c} for c in chunks]

        INDEXER.add(vectors, metas)

        total_chunks += len(chunks)
        uploaded_docs.append(filename)

    INDEXER.save()

    print("🔥 FINAL CHUNK COUNT:", len(INDEXER.meta))
    print("📂 WORKSPACE DOCS:", set(m["source"] for m in INDEXER.meta))

    options = [{"key": k, "label": v["label"]} for k, v in POSTPROCESS_OPTIONS.items()]

    return {
        "status": "ok",
        "documents": uploaded_docs,
        "total_chunks": total_chunks,
        "workspace_docs": list(set(m["source"] for m in INDEXER.meta)),
        "postprocess_options": options,
    }


   


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

@router.post("/logout")
async def logout():
        global INDEXER

        print("🧹 SESSION WIPE")

        if INDEXER is not None:
            INDEXER.reset()
            INDEXER = None

        # wipe raw folder
        for f in DATA_RAW.glob("*.pdf"):
            f.unlink()

        return {"status": "workspace cleared"}
@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
     fb = Feedback(
        name=body.name,
        email=body.email,
        subject=body.subject,
        message=body.message,
    )
     db.add(fb)
     db.commit()
     db.refresh(fb)

     return {"status": "ok"}


# ===========================
# Chat endpoint (RAG)
# ===========================
class ChatQuery(BaseModel):
    query: str
    k: int = 5
    document: str | None = None  # optional selected doc

@router.post("/chat")
async def chat(
    body: ChatQuery,
    indexer: FaissIndexer | None = Depends(get_indexer),
):
    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(
            status_code=404,
            detail="No index available. Upload documents first.",
        )

    try:
        # -----------------------------
        # Document-scoped search
        # -----------------------------
        if body.document:
            # temporarily filter metadata
            original_meta = indexer.meta

            filtered_meta = [
                m for m in original_meta
                if m.get("source") == body.document
            ]

            if filtered_meta:
                indexer.meta = filtered_meta

            result = run_rag(body.query, indexer, k=body.k)

            # restore original metadata
            indexer.meta = original_meta

            return result

        # -----------------------------
        # normal full search
        # -----------------------------
        result = run_rag(body.query, indexer, k=body.k)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

        # -----------------------------
        # default: full workspace search
        # -----------------------------
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
