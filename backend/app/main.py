from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import analytics, automation, candidates, comments, jobs, schedules, scorecards, users


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini ATS", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")

app.include_router(users.router)
app.include_router(candidates.router)
app.include_router(comments.router)
app.include_router(scorecards.router)
app.include_router(schedules.router)
app.include_router(jobs.router)
app.include_router(analytics.router)
app.include_router(automation.router)


@app.get("/health")
def health():
    return {"status": "ok"}
