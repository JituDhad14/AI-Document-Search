import fitz  # PyMuPDF

def load_pdf(file) -> str:
    """
    Reads a PDF file and returns its text content as a single string.
    `file` can be a file-like object (UploadFile.file from FastAPI).
    """
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text
