"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tasks, task_steps, priority, google_auth, classroom, notifications
from app.db.session import SessionLocal
from app.services.notifier import run_daily_notifications
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(
    title="The Last-Minute Life Saver",
    description="AI-powered productivity companion",
    version="0.4.0",
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
app.include_router(google_auth.router)
app.include_router(classroom.router)
app.include_router(notifications.router)


# Background Scheduler for Daily Notifications
scheduler = BackgroundScheduler()

def daily_notifications_job():
    db = SessionLocal()
    try:
        run_daily_notifications(db)
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    # Schedule the daily notification run at 8:00 AM UTC
    scheduler.add_job(daily_notifications_job, "cron", hour=8, minute=0)
    scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


@app.get("/", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": "The Last-Minute Life Saver", "version": "0.4.0"}
