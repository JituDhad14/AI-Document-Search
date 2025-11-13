from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the router module (routes are defined in backend/api/routes.py)
from backend.api import routes

app = FastAPI(title="RAG Doc Search API")

# Enable CORS (currently open to all — tighten in production!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the API routes under /api
app.include_router(routes.router, prefix="/api")

# Simple health endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}
