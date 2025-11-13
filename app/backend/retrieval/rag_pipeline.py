from typing import List
import os

# NOTE: Removed 'from dotenv import load_dotenv' 
# Since we are hardcoding the key, we don't need dotenv.

# Ensure you have the google-genai library installed: pip install google-genai
# If you are using another component that needs the embedder, keep this line.
from app.backend.ingestion.embedder import get_model 

# We need this for the correct function signature now
# We will import it inside call_genai for modularity, but listing it here as a note.
# import google.genai.types as types 

# -----------------------------
# Hardcoded Config 
# -----------------------------
# 🚨 YOUR HARDCODED GEMINI API KEY
# Reusing the provided key.
GEMINI_API_KEY = "AIzaSyCMgxzpNAWFuutEznGw7lHk5EvNsR04G_M" 
GEMINI_MODEL = "gemini-2.5-flash" 
GEMINI_TEMP = 0.0 # Will be passed inside the config object

LLM_PROVIDER = "genai" # Fixed to Gemini only

# -----------------------------
# LLM Calls
# -----------------------------
def call_genai(prompt: str) -> str:
    """
    Call Google Gemini / GenAI model. 
    🚨 FIX: Passes 'temperature' inside a GenerateContentConfig object.
    """
    if not GEMINI_API_KEY:
        return "Internal error: GEMINI_API_KEY is unset in code." 
    try:
        from google import genai
        # We need the types module to create the configuration object
        from google.genai import types 
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 1. Create the generation configuration object
        generation_config = types.GenerateContentConfig(
            temperature=GEMINI_TEMP,
            # Add other parameters like max_output_tokens, top_p, etc., here if needed
        )

        # 2. Pass the config object using the 'config' keyword argument
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=generation_config, # 🚨 FIX IS HERE
        )

        return getattr(response, "text", str(response))
    except Exception as e:
        # This will now catch network/authentication errors from the API
        return f"GenAI error: {e}"

def call_llm(prompt: str) -> str:
    """Wrapper to call Gemini."""
    return call_genai(prompt)

# -----------------------------
# Build prompt for RAG
# -----------------------------
def build_prompt(query: str, contexts: List[dict]) -> str:
    """Build a context-rich prompt for the LLM using retrieved chunks."""
    prompt = "Answer the question based on the following context:\n\n"
    for c in contexts:
        if not isinstance(c, dict):
            continue
        src = c.get("source", f"chunk_{c.get('id', 'unknown')}")
        text = c.get("text", "")
        prompt += f"Source: {src}\n{text}\n\n"
    prompt += f"Question: {query}\nAnswer:"
    return prompt

# -----------------------------
# Run RAG (Updated for Debugging Retrieval)
# -----------------------------
def run_rag(query: str, indexer, k: int = 5) -> dict:
    """
    Run RAG: retrieve top-k chunks, build prompt, call Gemini.
    Returns dict with answer and sources.
    """
    if indexer.index is None or len(indexer.meta) == 0:
        return {"error": "No index available. Upload documents first.", "query": query}

    # 1. Retrieve top-k contexts
    contexts = indexer.retrieve(query, k=k)

    # 🚨 DEBUGGING STEP: Print the retrieved content to the terminal
    print("\n--- RETRIEVED CONTEXTS ---")
    if contexts:
        for i, c in enumerate(contexts):
            source = c.get("source", "Unknown Source")
            text_snippet = c.get("text", "")[:200] + "..." # Print first 200 chars
            print(f"Chunk {i+1} (Source: {source}): {text_snippet}")
    else:
        print("No contexts retrieved.")
    print("--------------------------\n")
    # ----------------------------------------------------

    # 2. Build prompt
    prompt = build_prompt(query, contexts)

    # 3. Call Gemini LLM
    answer = call_llm(prompt)

    return {
        "query": query,
        "answer": answer,
        "sources": sorted(list(set([c["source"] for c in contexts]))),
    }