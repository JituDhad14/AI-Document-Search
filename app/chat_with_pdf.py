from pathlib import Path
from app.backend.ingestion.indexer import Indexer
from app.backend.ingestion.embedder import get_model
from app.backend.retrieval.rag_pipeline import run_rag
import fitz  # PyMuPDF
import numpy as np

# -----------------------------
# Config
# -----------------------------
RAW_DIR = Path("app/data/raw/")  # Folder containing uploaded PDFs
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap for better context in RAG

# -----------------------------
# PDF Processing / Chunking
# -----------------------------
def load_pdf(path: str) -> str:
    """Load text from a PDF file with PyMuPDF."""
    doc = fitz.open(path)
    text_parts = [page.get_text("text") for page in doc]
    doc.close()
    return "\n".join(text_parts)

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks

def ingest_pdf(file_path: str, indexer: Indexer):
    """
    Load PDF, split into chunks, embed, and add to FAISS index.
    Now fully safe against 'str' or shape errors.
    """
    try:
        text = load_pdf(file_path)
    except Exception as e:
        print(f"❌ Failed to load {file_path}: {e}")
        return

    chunks = chunk_text(text)
    model = get_model()

    print(f"🔹 Generating embeddings for {len(chunks)} chunks...")
    embeddings = model.encode(chunks, show_progress_bar=True)

    # ✅ Convert to float32 NumPy array safely
    if isinstance(embeddings, list):
        embeddings = np.array(embeddings, dtype="float32")
    elif not isinstance(embeddings, np.ndarray):
        embeddings = np.array([embeddings], dtype="float32")

    # ✅ Sanity check
    if embeddings.ndim != 2:
        raise ValueError(f"Expected 2D embeddings, got shape: {embeddings.shape}")

    # Prepare metadata
    metas = [{"source": Path(file_path).name, "text": chunk} for chunk in chunks]

    # ✅ Add to FAISS index
    indexer.add(embeddings, metas, clear_existing=False)
    indexer.save()

    print(f"✅ Ingested {len(chunks)} chunks from {file_path}")

# -----------------------------
# Main Chat Loop
# -----------------------------
def main():
    print("AI PDF Chatbot - Ask something about the uploaded PDFs")

    # Initialize FAISS indexer
    dim = get_model().get_sentence_embedding_dimension()
    indexer = Indexer(dim=dim)

    # -----------------------------
    # Single PDF ingestion for testing
    # -----------------------------
    print("🧩 Testing mode: Using a single PDF for ingestion...")

    # Always reset the index for single-PDF testing
    indexer.reset()

    single_pdf_path = RAW_DIR / "DataMining-Unit-1.pdf"  # Change filename if needed
    if single_pdf_path.exists():
        ingest_pdf(str(single_pdf_path), indexer)
        print("✅ Single PDF ingestion complete.\n")
    else:
        print(f"❌ PDF not found: {single_pdf_path}")
        return  # Exit early if the PDF doesn't exist

    # -----------------------------
    # Chat loop
    # -----------------------------
    while True:
        query = input("Ask something (or type 'exit' to quit): ").strip()
        if query.lower() in ("exit", "quit"):
            print("Exiting AI PDF Chatbot.")
            break

        try:
            result = run_rag(query, indexer, k=5)

            if "error" in result:
                print("Error:", result["error"])
            else:
                print("\nQuery:", result["query"])
                print("Answer:", result["answer"])
                print("Sources:", ", ".join(result["sources"]))
                print("\n" + "-" * 50 + "\n")
        except Exception as e:
            print("❌ Error during RAG processing:", e)

if __name__ == "__main__":
    main()
