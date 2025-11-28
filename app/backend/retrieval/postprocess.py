# app/backend/retrieval/postprocess.py
from typing import List, Dict
from app.backend.retrieval.rag_pipeline import build_prompt, call_llm  # reuse existing functions
from app.backend.ingestion.indexer import Indexer
import textwrap

# Map option key -> (friendly label, prompt wrapper)
POSTPROCESS_OPTIONS = {
    "quick_summary": {
        "label": "Quick summary",
        "template": lambda doc_title: (
            "You are a helpful summarization assistant. Produce a short concise summary (3-5 sentences) "
            f"of the document titled: {doc_title}. Focus on the main idea and key conclusions.\n\nContext:\n"
        )
    },
    "key_points": {
        "label": "Key points",
        "template": lambda doc_title: (
            "You are an assistant that extracts the most important takeaways. Provide an ordered list of the "
            f"top 8–12 key points from the document titled: {doc_title}.\n\nContext:\n"
        )
    },
    "outline": {
        "label": "Structured outline (TOC)",
        "template": lambda doc_title: (
            "You are an assistant that builds an outline or table of contents from document chunks. Produce a "
            f"hierarchical outline with short headings and indicate page numbers where available for: {doc_title}.\n\nContext:\n"
        )
    },
    "entities": {
        "label": "Important entities & facts",
        "template": lambda doc_title: (
            "Extract named entities, important facts, numbers, dates, metrics, and definitions from the document titled: "
            f"{doc_title}. Present them as short labeled bullets grouped by type (People, Organizations, Dates, Numbers, Terms).\n\nContext:\n"
        )
    },
    "faqs": {
        "label": "Auto-generated FAQs",
        "template": lambda doc_title: (
            "Create 6 concise FAQ pairs (question + short answer) that a reader would ask after reading the document titled: "
            f"{doc_title}. Use the provided context to answer.\n\nContext:\n"
        )
    },
}

def build_option_prompt(option_key: str, doc_title: str, contexts: List[dict]) -> str:
    """Create a final prompt for the LLM using the contexts returned from FAISS."""
    opt = POSTPROCESS_OPTIONS[option_key]
    header = opt["template"](doc_title)
    # Attach contexts (reuse build_prompt style)
    # We'll include the header plus the retrieved context chunks.
    ctx_text = ""
    for c in contexts:
        src = c.get("source", "unknown")
        page = c.get("page")
        snippet = c.get("text", "")[:500]
        if page:
            ctx_text += f"Source: {src} (page {page})\n{snippet}\n\n"
        else:
            ctx_text += f"Source: {src}\n{snippet}\n\n"
    # Final instruction
    footer = "\nRespond concisely and use bullet lists when appropriate. If information is missing say 'Not found in the document.'"
    return header + ctx_text + footer

def process_option(option_key: str, query: str, indexer: Indexer, k: int = 5) -> Dict:
    """
    Run retrieval for 'query' over indexer, then call LLM with an option-specific prompt.
    query: a short instruction like 'document summary for <filename>' or the filename itself.
    """
    # Retrieve top-k contexts (indexer.retrieve returns metas with page if you updated it)
    contexts = indexer.retrieve(query, k=k)

    # If no contexts, return a helpful message
    if not contexts:
        return {"result": "No relevant content retrieved from the index.", "sources": []}

    # Build prompt
    # We'll use query as document title if that's what you pass
    prompt = build_option_prompt(option_key, query, contexts)

    # Call the LLM via existing wrapper
    answer = call_llm(prompt)

    # Build sources list (unique)
    sources = sorted(list({ (c.get("source"), c.get("page")) for c in contexts }))

    return {"result": answer, "sources": sources}
