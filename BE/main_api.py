from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.embedding_services.api import router as embedding_router
from src.pdf_processing.api import router as pdf_router
from src.agents.api import router as agent_router

app = FastAPI(
    title="Control Theory Textbook API",
    description="API for processing PDFs, indexing content, and answering questions via agents.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(embedding_router)
app.include_router(pdf_router)
app.include_router(agent_router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Control Theory Textbook API",
        "docs": "/docs",
        "health": "/health"  # Note: /health is in embedding_router, maybe we should move it or have a global one
    }