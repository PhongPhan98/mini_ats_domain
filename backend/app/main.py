from pathlib import Path
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.email_scheduler import process_due_email_schedules
from app.routers import analytics, applications, audit, auth, automation, candidates, comments, jobs, offers, reports, schedules, scorecards, users, activity, public_jobs, interviews


async def _email_scheduler_loop():
    interval = max(15, int(settings.email_scheduler_interval_seconds))
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(process_due_email_schedules)
        except Exception:
            # A transient database or SMTP failure must not stop the API.
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.frontend_base_url.lower().startswith("https://") and settings.auth_jwt_secret in {"change-me", "local-development-only"}:
        raise RuntimeError("Set a strong AUTH_JWT_SECRET before starting the production API")
    scheduler = asyncio.create_task(_email_scheduler_loop())
    try:
        yield
    finally:
        scheduler.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler


app = FastAPI(title="Mini ATS", version="0.2.0", lifespan=lifespan)

origins = [o.strip().rstrip("/") for o in settings.cors_origins.split(",") if o.strip()]
frontend_origin = settings.frontend_base_url.strip().rstrip("/")
if frontend_origin and frontend_origin not in origins:
    origins.append(frontend_origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(activity.router)
app.include_router(public_jobs.router)
app.include_router(applications.router)
app.include_router(users.router)
app.include_router(candidates.router)
app.include_router(comments.router)
app.include_router(scorecards.router)
app.include_router(schedules.router)
app.include_router(interviews.router)
app.include_router(jobs.router)
app.include_router(offers.router)
app.include_router(analytics.router)
app.include_router(reports.router)
app.include_router(automation.router)


@app.get("/health")
def health():
    return {"status": "ok"}

