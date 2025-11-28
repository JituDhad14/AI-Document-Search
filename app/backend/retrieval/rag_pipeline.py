# app/backend/retrieval/rag_pipeline.py

from typing import List
import os
from app.backend.ingestion.embedder import get_model


# -----------------------------
# Config (Hardcoded for now)
# -----------------------------
# ⚠️ This should NOT be pushed to GitHub.
GEMINI_API_KEY = "AIzaSyCMgxzpNAWFuutEznGw7lHk5EvNsR04G_M"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TEMP = 0.0

LLM_PROVIDER = "genai"


# -----------------------------
# LLM Calls (Gemini / GenAI)
# -----------------------------
def call_genai(prompt: str) -> str:
    """Call Gemini model using hardcoded API key (for now)."""

    if not GEMINI_API_KEY:
        return "Internal error: GEMINI_API_KEY is not set."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        generation_config = types.GenerateContentConfig(
            temperature=GEMINI_TEMP,
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=generation_config,
        )

        return getattr(response, "text", str(response))

    except Exception as e:
        return f"GenAI error: {e}"


def call_llm(prompt: str) -> str:
    return call_genai(prompt)


# -----------------------------
# Prompt Building
# -----------------------------
def build_prompt(query: str, contexts: List[dict]) -> str:
    prompt = "Answer the question based on the following context:\n\n"
    for c in contexts:
        src = c.get("source", "unknown")
        text = c.get("text", "")
        prompt += f"Source: {src}\n{text}\n\n"
    prompt += f"Question: {query}\nAnswer:"
    return prompt


# -----------------------------
# Run RAG
# -----------------------------
def run_rag(query: str, indexer, k: int = 5) -> dict:
    if indexer.index is None or len(indexer.meta) == 0:
        return {"error": "No index available. Upload documents first.", "query": query}

    contexts = indexer.retrieve(query, k=k)

    print("\n--- RETRIEVED CONTEXTS ---")
    for i, c in enumerate(contexts):
        source = c.get("source", "Unknown")
        snippet = c.get("text", "")[:200] + "..."
        print(f"Chunk {i+1} (Source: {source}): {snippet}")
    print("--------------------------\n")

    prompt = build_prompt(query, contexts)
    answer = call_llm(prompt)

    sources = sorted(list(set([c.get("source", "unknown") for c in contexts])))

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
    }
