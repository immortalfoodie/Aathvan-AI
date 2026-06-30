"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tasks, task_steps, priority

app = FastAPI(
    title="The Last-Minute Life Saver",
    description="AI-powered productivity companion",
    version="0.3.0",
)

# CORS — allow the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(task_steps.router)
app.include_router(priority.router)


@app.get("/", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": "The Last-Minute Life Saver", "version": "0.1.0"}
