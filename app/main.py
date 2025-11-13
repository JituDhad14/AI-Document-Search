from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the routes using a specific alias
from app.backend.api import routes as api_routes

app = FastAPI(title="RAG Doc Search API")

# Enable CORS (Allows client script to talk to the server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Allow all origins for local testing
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under /api
# 🚨 FIX: Using the correct alias (api_routes) to access the router object
app.include_router(api_routes.router, prefix="/api")

# Root route
@app.get("/")
async def root():
    return {"message": "AI PDF Chatbot API running"}

# Health check route
@app.get("/health")
async def health():
    return {"status": "ok"}
