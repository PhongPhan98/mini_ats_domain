# Mini ATS (Full-stack)

A mini Applicant Tracking System for recruiters.

## Features

1. CV Upload (PDF/DOCX)
2. CV Parsing (rule-based, no external LLM required)
3. Candidate Database + Search/Filter
4. Candidate Dashboard + Analytics
5. Job Description Input
6. Rule-based Matching (score + explanation)
7. End-to-end automation flow:
   Upload -> Parse -> Save -> Display -> Match

## Tech Stack

- Frontend: Next.js (React)
- Backend: FastAPI (Python)
- Database: PostgreSQL (SQLAlchemy)
- AI: Optional (OpenAI/Gemini); default flow uses local rule-based parsing + matching
- Storage: Local filesystem (`backend/uploads`) (easy to swap with S3)

## Project Structure

```bash
mini_ats/
  backend/
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      prompts.py
      routers/
        candidates.py
        jobs.py
        analytics.py
      services/
        parser.py
        llm.py
        storage.py
    requirements.txt
    .env.example
  frontend/
    src/app/
      page.tsx
      upload/page.tsx
      jobs/page.tsx
      candidates/[id]/page.tsx
    src/lib/api.ts
    package.json
    .env.local.example
  docker-compose.yml
```

## One-command Run Scripts

From project root:

```bash
./scripts/run_backend.sh
./scripts/run_frontend.sh
# or start both
./scripts/run_all.sh
```

Behavior improvements:
- `run_all.sh` auto-checks Postgres on `:5432` and tries `docker compose up -d db` if needed.
- `run_backend.sh` auto-kills occupied backend port by default when called via `run_all.sh`.
- `run_frontend.sh` auto-finds the next free port if 3000 is busy.
- Ctrl+C in `run_all.sh` stops both services.

Useful overrides:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=3002 ./scripts/run_all.sh
MINI_ATS_AUTO_KILL=0 ./scripts/run_all.sh
```

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### Optional LLM Provider Switch (OpenAI/Gemini)

Set in `backend/.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.0-flash-lite
```

Or use OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Database

Start postgres quickly:

```bash
docker compose up -d db
```

Tables are auto-created on backend startup (`Base.metadata.create_all`).

## API Endpoints

### Candidate
- `POST /api/candidates/upload` (multipart file)
- `GET /api/candidates?skills=python&skills=fastapi&min_experience=3&keyword=fintech`
- `GET /api/candidates/{id}`
- `PATCH /api/candidates/{id}` (manual correction after parsing)
- `GET /api/candidates/skills/catalog` (current skill dictionary)

### Analytics
- `GET /api/analytics/summary`

### Jobs + Matching
- `POST /api/jobs`
- `GET /api/jobs`
- `POST /api/jobs/{job_id}/match`

## LLM Prompts Included

- CV parsing prompt: `backend/app/prompts.py::CV_PARSING_PROMPT`
- Candidate-job matching prompt: `backend/app/prompts.py::MATCHING_PROMPT`

## Notes

- Current default upload + matching pipeline is fully local, rule-based (no external LLM calls). Parsed JSON now includes per-field confidence + overall confidence score.

- For production, replace local storage with S3 and signed URLs.
- Add auth (JWT) and role-based access for recruiter teams.
- Add background workers (Celery/RQ) for async parsing at scale.
