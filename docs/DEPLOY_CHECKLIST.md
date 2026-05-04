# Mini ATS Deployment Checklist

## 1) Environment
- [ ] AUTH_ALLOW_DEV_HEADERS=false
- [ ] AUTH_JWT_SECRET set (strong random)
- [ ] GOOGLE_CLIENT_ID / SECRET / REDIRECT_URI configured
- [ ] NEXT_PUBLIC_API_BASE points to production backend
- [ ] SMTP_HOST/PORT/USER/PASSWORD/FROM set
- [ ] LLM provider + key configured (if AI enabled)
- [ ] Rotate any leaked/old API keys

## 2) Deploy Targets
- Frontend: Vercel (root `frontend`)
- Backend: Render/Railway/Fly (root `backend`)
- DB: Managed Postgres

## 3) Post-Deploy Smoke
- [ ] Login works (Google)
- [ ] Upload CV parse -> review -> save works
- [ ] Jobs matching runs (AI/Rule mode visible)
- [ ] Pipeline stage move works
- [ ] Candidate interview schedule works
- [ ] Public job page `/jobs/:slug` + apply works
- [ ] Activity log page renders
- [ ] Notifications render

## 4) Security
- [ ] HTTPS only
- [ ] secure cookies in production
- [ ] public apply rate limit tested (429 behavior)
