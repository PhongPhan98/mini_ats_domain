# Mini ATS

A production-oriented **Applicant Tracking System (ATS)** built for recruiter teams.

This project supports end-to-end hiring operations: CV ingestion, parsing, candidate management, collaboration, interview workflow, job matching, automation, analytics, reporting, and role-based access.

---

## 1) Business Flows

## 1.1 Candidate Intake & Parsing
1. Recruiter uploads one or multiple CVs (PDF/DOCX).
2. System parses CV into structured profile fields.
3. Recruiter reviews/edits parsed data in parse-first UI.
4. Candidate is imported into ATS with ownership metadata.

### Parsing logic (current)
- Rule-based extraction with EN/VI support.
- Section-aware extraction (skills/experience/education/projects/certifications/languages).
- Confidence output per field + overall confidence score.
- Layered PDF extraction pipeline:
  - pypdf first
  - pdfplumber fallback
  - OCR fallback (pdf2image + pytesseract) for scanned PDFs

---

## 1.2 Candidate Management
- Recruiters manage candidates through ATS stages:
  - applied → screening → interview → offer → hired/rejected
- Soft delete + restore via Trash.
- Candidate detail includes:
  - profile info
  - CV files
  - comments/mentions
  - schedules
  - scorecards
  - timeline

---

## 1.3 Collaboration & Ownership
Ownership-first model:
- Recruiter sees/manages own candidates/jobs by default.
- Shared/invited access supports collaboration.

Current collaboration flows:
1. **Comment mentions**: @mention another HR.
2. **Share invitation**:
   - HR A invites HR B
   - HR B approves/rejects in notifications
   - On approve, system clones candidate record and assigns owner=HR B
3. **Ownership request**:
   - HR can request ownership transfer
   - owner/admin approves/rejects

View-only behavior:
- Non-owner HR (view rights) can see limited candidate page and comment.
- No edit/delete/submit actions unless owner.

---

## 1.4 Job & Matching Flow
1. HR creates job title + requirements.
2. Configure threshold per job.
3. Run matching to get ranked candidates + explanations.
4. Shortlist directly from match result.

Matching evolution:
- **Phase 1/2/3 hybrid rule engine** now includes:
  - required skills overlap
  - experience fit
  - title normalization + fuzzy title similarity
  - keyword/context relevance
  - optional embedding-based semantic relevance (feature flag)

---

## 1.5 Notifications
- Mention notifications.
- Share invitation inbox.
- Ownership request updates.
- Read-aware badge count (hide when zero).

---

## 1.6 Analytics & Reporting
- Dashboard metrics and funnel views.
- Source effectiveness & conversion metrics.
- Weekly hiring trend, stage aging.
- Export formats: CSV/XLSX/PDF.

---

## 1.7 Auth & Access Control
- Google OAuth login + JWT cookie session.
- Strict auth mode supported.
- Role-based access (admin/recruiter/interviewer/hiring_manager).
- Admin user management + audit logs.

---

## 2) Technical Architecture

## 2.1 Stack
- **Frontend**: Next.js 14 (App Router), React, TypeScript
- **Backend**: FastAPI, SQLAlchemy
- **Database**: PostgreSQL
- **Storage**: Local filesystem (`uploads/`) by default
- **Optional AI**: OpenAI/Gemini for other services; matching/parsing core runs locally

## 2.2 Key Backend Modules
- `app/routers/`:
  - `auth.py`, `users.py`, `audit.py`
  - `candidates.py`, `comments.py`, `jobs.py`
  - `analytics.py`, `reports.py`
  - `automation.py`, `schedules.py`, `scorecards.py`
- `app/services/`:
  - `parser.py` (PDF/DOCX extraction + OCR fallback)
  - `rule_based.py` (parse + matching logic)
  - `storage.py`, `audit.py`, `automation.py`, `llm.py`

## 2.3 Frontend Main Pages
- `/` dashboard
- `/upload` parse-first CV import
- `/candidates/[id]` candidate workspace
- `/jobs` jobs + matching
- `/pipeline` stage pipeline
- `/automation`, `/notifications`, `/users`, `/audit`, `/login`

---

## 3) Database Design (Core Entities)

## users
- `id` (PK)
- `email` (unique)
- `full_name`
- `role` (admin/recruiter/interviewer/hiring_manager)
- `created_at`

## candidates
- `id` (PK)
- `name`, `email`, `phone`
- `status`
- `years_of_experience`
- `summary`
- `education` (JSONB)
- `previous_companies` (JSONB)
- `skills` (JSONB)
- `parsed_json` (JSONB: owner metadata, timeline, collab/share/request state, confidence, etc.)
- `created_at`

## candidate_files
- `id` (PK)
- `candidate_id` (FK candidates)
- `file_url`, `original_filename`, `uploaded_at`

## candidate_comments
- `id` (PK)
- `candidate_id` (FK)
- `author_user_id` (FK users)
- `body`
- `mentions` (JSONB)
- `created_at`

## interview_scorecards
- `id` (PK)
- `candidate_id` (FK)
- `interviewer_user_id` (FK users)
- `interview_stage`
- `criteria_scores` (JSONB)
- `overall_score`, `recommendation`, `summary`, `created_at`

## interview_schedules
- `id` (PK)
- `candidate_id` (FK)
- `organizer_user_id` (FK users)
- `interviewer_email`
- `scheduled_at`, `duration_minutes`
- `meeting_link`, `notes`, `created_at`

## jobs
- `id` (PK)
- `title`
- `requirements`
- `created_at`
- (ownership + settings handled in routers/metadata)

---

## 4) How to Build & Run

## 4.1 Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- (Optional OCR) `tesseract-ocr`, `poppler-utils`

## 4.2 Quick Run (scripts)
From project root:

```bash
./scripts/run_backend.sh
./scripts/run_frontend.sh
# or run both
./scripts/run_all.sh
```

Useful overrides:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=3002 ./scripts/run_all.sh
MINI_ATS_AUTO_KILL=0 ./scripts/run_all.sh
```

---

## 4.3 Manual Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

---

## 4.4 Manual Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

---

## 4.5 Database Setup

Using docker compose:

```bash
docker compose up -d db
```

The app uses SQLAlchemy table creation on startup (`Base.metadata.create_all`).

Default sample connection in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/mini_ats
```

---

## 4.6 Important Environment Variables

## Auth
```env
AUTH_JWT_SECRET=change-me
AUTH_ALLOW_DEV_HEADERS=false
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
GOOGLE_ALLOWED_DOMAIN=
AUTH_BOOTSTRAP_ADMIN_EMAIL=
```

## Matching Phase 3 (optional semantic rerank)
```env
MATCHING_ENABLE_EMBEDDINGS=false
MATCHING_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## OCR dependencies (Phase 1 parsing enhancements)
Python packages are in `requirements.txt`.
System tools needed for OCR:
- `tesseract-ocr`
- `poppler-utils`

---

## 5) API Surface (high level)

## Candidates
- `POST /api/candidates/parse`
- `POST /api/candidates/upload`
- `GET /api/candidates`
- `GET /api/candidates/{id}`
- `PATCH /api/candidates/{id}`
- `DELETE /api/candidates/{id}`
- `POST /api/candidates/{id}/restore`
- share/invite/ownership/notifications endpoints

## Jobs
- `POST /api/jobs`
- `GET /api/jobs`
- `PATCH /api/jobs/{id}`
- `POST /api/jobs/{id}/match`
- `GET/PATCH /api/jobs/{id}/settings`

## Automation / Analytics / Reports
- `/api/automation/*`
- `/api/analytics/summary`
- `/api/reports/*`

## Auth / Admin
- `/api/auth/*`
- `/api/users/*`
- `/api/audit/*`

---

## 6) Current Product Status

Implemented:
- parse-first multi-CV workflow
- ownership + collaboration controls
- notifications + mentions
- audit logging
- strict auth option with Google OAuth
- EN/VI UX improvements
- upgraded rule-based parsing & matching (Phase 1/2/3)

Planned next:
- model calibration tooling for match weights
- benchmark dataset + automated quality checks
- optional vector store for large-scale semantic retrieval

---

## 7) License & Notes
Internal project for product development. Adapt architecture and security hardening before public production deployment.


## 8) Architecture Diagram

```mermaid
graph TD
  U[Recruiter / HR User] --> FE[Next.js Frontend]
  FE --> API[FastAPI Backend]
  API --> DB[(PostgreSQL)]
  API --> FS[(Local File Storage: uploads/)]

  API --> PARSER[Parser Service
PDF/DOCX + OCR fallback]
  API --> MATCH[Rule-based Matching
+ Title Fuzzy + Optional Embedding]
  API --> AUTH[Google OAuth + JWT Cookie]
  API --> AUDIT[Audit Log Service]
```

## 9) Sequence Diagrams

### 9.1 CV Upload -> Parse -> Import

```mermaid
sequenceDiagram
  participant HR as Recruiter
  participant FE as Frontend
  participant BE as Backend
  participant PS as Parser Service
  participant DB as PostgreSQL

  HR->>FE: Upload CV(s)
  FE->>BE: POST /api/candidates/parse
  BE->>PS: Extract text (pypdf/docx)
  alt weak PDF text
    PS->>PS: fallback pdfplumber
    PS->>PS: fallback OCR (pdf2image+pytesseract)
  end
  PS-->>BE: Parsed fields + confidence
  BE-->>FE: Preview JSON
  HR->>FE: Review/edit + Import
  FE->>BE: POST /api/candidates/upload
  BE->>DB: Insert candidate + metadata
  BE-->>FE: Candidate created
```

### 9.2 Share Invitation -> Approve -> Clone Ownership

```mermaid
sequenceDiagram
  participant A as HR A (Owner)
  participant B as HR B
  participant FE as Frontend
  participant BE as Backend
  participant DB as PostgreSQL

  A->>FE: Send share invite to HR B
  FE->>BE: POST /api/candidates/{id}/share
  BE->>DB: Save pending invitation

  B->>FE: Open notifications
  FE->>BE: GET /api/candidates/share/invitations?scope=inbox
  BE-->>FE: Pending invitation list

  B->>FE: Approve & Clone
  FE->>BE: POST /api/candidates/{id}/share/invitations/{invite_id}/decision
  BE->>DB: Clone candidate + files (owner=HR B)
  BE-->>FE: clone_candidate_id
  FE-->>B: Redirect to cloned candidate page
```

### 9.3 Job Matching Run

```mermaid
sequenceDiagram
  participant HR as Recruiter
  participant FE as Frontend
  participant BE as Backend
  participant RM as Rule Match Engine
  participant DB as PostgreSQL

  HR->>FE: Run matching for Job X
  FE->>BE: POST /api/jobs/{job_id}/match?threshold=...
  BE->>DB: Load job + visible candidates
  BE->>RM: Score each candidate
  RM->>RM: skills + exp + title fuzzy + keyword
  opt embeddings enabled
    RM->>RM: semantic similarity (sentence-transformers)
  end
  RM-->>BE: score + explanation
  BE-->>FE: ranked candidates above threshold
```
