import json
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings

DEFAULT_SKILL_ALIASES: dict[str, list[str]] = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "c#": ["c#", "csharp", ".net", "dotnet"],
    "c++": ["c++", "cpp"],
    "go": ["golang", "go"],
    "ruby": ["ruby"],
    "php": ["php"],
    "dart": ["dart"],
    "react": ["react", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "vue": ["vue", "vuejs"],
    "angular": ["angular"],
    "flutter": ["flutter"],
    "react native": ["react native"],
    "node.js": ["node.js", "nodejs"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "spring": ["spring", "spring boot"],
    "nestjs": ["nestjs"],
    "express": ["express", "expressjs"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic"],
    "sqlite": ["sqlite"],
    "sql server": ["sql server", "mssql"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure"],
    "terraform": ["terraform"],
    "linux": ["linux"],
    "git": ["git"],
    "github": ["github"],
    "gitlab": ["gitlab"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration"],
    "jenkins": ["jenkins"],
    "rest": ["rest", "restful"],
    "graphql": ["graphql"],
    "microservices": ["microservice", "microservices"],
    "system design": ["system design"],
    "html": ["html"],
    "css": ["css"],
    "tailwind": ["tailwind", "tailwindcss"],
    "bootstrap": ["bootstrap"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "machine learning": ["machine learning", "ml"],
    "data analysis": ["data analysis", "phan tich du lieu"],
}


def _load_skill_aliases() -> dict[str, list[str]]:
    path = Path(__file__).resolve().parents[1] / "data" / "skills_vn_en.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): [str(x) for x in (v or [])] for k, v in data.items()}
    except Exception:
        pass
    return DEFAULT_SKILL_ALIASES


SKILL_ALIASES = _load_skill_aliases()

SECTION_HEADER_HINTS = {
    "education", "experience", "work experience", "projects", "skills", "certifications",
    "contact", "objective", "summary", "profile", "thong tin lien he", "kinh nghiem",
    "hoc van", "du an", "ky nang", "chung chi", "muc tieu", "tom tat",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")
LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/[^\s]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/[^\s]+", re.IGNORECASE)
YEARS_EXPLICIT_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:years?|yrs?|nam)\s*(?:of\s+)?(?:experience|kinh\s*nghiem)?",
    re.IGNORECASE,
)
YEAR_RANGE_RE = re.compile(
    r"((?:19|20)\d{2})\s*(?:-|–|to)\s*(present|current|now|nay|hien\s*tai|(?:19|20)\d{2})",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _match_normalize(text: str) -> str:
    text = _strip_accents(text.lower())
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _looks_like_section_header(line: str) -> bool:
    compact = _match_normalize(line)
    return compact in {_match_normalize(x) for x in SECTION_HEADER_HINTS}






def _clean_lines(items: list[str], min_len: int = 3, max_items: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        line = re.sub(r"\s+", " ", (raw or "").strip("-•* 	"))
        if len(line) < min_len:
            continue
        key = _match_normalize(line)
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= max_items:
            break
    return out

def _extract_sections(lines: list[str]) -> dict[str, list[str]]:
    section_aliases = {
        "experience": ["experience", "work experience", "employment", "kinh nghiem"],
        "education": ["education", "hoc van", "academic"],
        "skills": ["skills", "ky nang", "tech stack"],
        "projects": ["projects", "du an"],
        "certifications": ["certifications", "chung chi", "certificate"],
        "languages": ["languages", "ngoai ngu", "language"],
    }

    def detect(line: str) -> str | None:
        lm = _match_normalize(line)
        for key, aliases in section_aliases.items():
            if any(_match_normalize(a) == lm or _match_normalize(a) in lm for a in aliases):
                return key
        return None

    sections: dict[str, list[str]] = {k: [] for k in section_aliases}
    current: str | None = None
    for line in lines:
        hit = detect(line)
        if hit:
            current = hit
            continue
        if current:
            sections[current].append(line)
    return sections


def _extract_projects(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        if len(clean) < 4:
            continue
        out.append(clean[:180])
        if len(out) >= 8:
            break
    return out

def _extract_name(lines: list[str]) -> str | None:
    blacklist = {
        "cv", "resume", "curriculum vitae", "email", "phone", "contact", "linkedin", "github",
        "thong tin", "kinh nghiem", "hoc van", "ky nang",
    }

    for line in lines[:10]:
        clean = line.strip().strip("-•|:")
        if not clean or len(clean) > 60:
            continue

        lower = _match_normalize(clean)
        if any(token in lower for token in blacklist):
            continue
        if _looks_like_section_header(clean):
            continue

        words = clean.split()
        if not (2 <= len(words) <= 5):
            continue

        alpha_ratio = sum(ch.isalpha() for ch in clean) / max(1, len(clean))
        if alpha_ratio < 0.6:
            continue

        if clean.isupper() or sum(w[:1].isupper() for w in words) >= max(2, len(words) - 1):
            return clean

    return None


def _extract_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None


def _extract_phone(text: str) -> str | None:
    for m in PHONE_RE.finditer(text):
        candidate = re.sub(r"\s+", " ", m.group(1)).strip()
        digits = re.sub(r"\D", "", candidate)
        if 9 <= len(digits) <= 15:
            if digits.startswith("84") or digits.startswith("0"):
                return candidate
    for m in PHONE_RE.finditer(text):
        candidate = re.sub(r"\s+", " ", m.group(1)).strip()
        digits = re.sub(r"\D", "", candidate)
        if 9 <= len(digits) <= 15:
            return candidate
    return None


def _extract_skills(text: str) -> list[str]:
    normalized = _match_normalize(text)
    found: set[str] = set()

    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            probe = _match_normalize(alias)
            pattern = rf"(?<![a-z0-9]){re.escape(probe)}(?![a-z0-9])"
            if re.search(pattern, normalized):
                found.add(canonical)
                break

    return sorted(found)


def _extract_years_of_experience(text: str) -> int | None:
    explicit = [int(x) for x in YEARS_EXPLICIT_RE.findall(_match_normalize(text))]
    if explicit:
        return max(0, min(50, max(explicit)))

    current_year = datetime.now().year
    inferred: list[int] = []
    for start, end in YEAR_RANGE_RE.findall(_match_normalize(text)):
        s = int(start)
        e = current_year if end.lower() in {"present", "current", "now", "nay", "hien tai"} else int(end)
        if 1980 <= s <= current_year and s <= e <= current_year:
            inferred.append(e - s)

    if inferred:
        return max(0, min(50, max(inferred)))
    return None


def _extract_education(lines: list[str]) -> list[str]:
    edu_keys = (
        "university", "college", "bachelor", "master", "phd", "engineer",
        "dai hoc", "cao dang", "cu nhan", "thac si", "hoc vien",
    )
    out: list[str] = []
    for line in lines:
        l = _match_normalize(line)
        if any(k in l for k in edu_keys):
            out.append(line.strip())
        if len(out) >= 6:
            break
    return out


def _extract_previous_companies(lines: list[str]) -> list[str]:
    company_keys = (
        "company", "corp", "inc", "ltd", "llc", "jsc", "co.,", "co ",
        "cong ty", "tnhh", "co phan", "tap doan",
    )
    out: list[str] = []
    for line in lines:
        l = _match_normalize(line)
        if any(k in l for k in company_keys):
            out.append(line.strip())
        if len(out) >= 10:
            break
    return out




def _extract_linkedin(text: str) -> str | None:
    m = LINKEDIN_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_github(text: str) -> str | None:
    m = GITHUB_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_location(lines: list[str]) -> str | None:
    hints = ("ho chi minh", "hanoi", "da nang", "vietnam", "tp.hcm", "ha noi", "remote")
    for line in lines[:20]:
        ll = _match_normalize(line)
        if any(h in ll for h in hints):
            return line.strip()[:120]
    return None


def _extract_headline(lines: list[str]) -> str | None:
    role_hints = ("developer", "engineer", "designer", "tester", "qa", "data", "product", "manager", "devops", "frontend", "backend", "fullstack")
    for line in lines[:15]:
        ll = _match_normalize(line)
        if any(h in ll for h in role_hints) and len(line.strip()) <= 120:
            return line.strip()
    return None


def _extract_certifications(lines: list[str]) -> list[str]:
    out = []
    hints = ("cert", "certificate", "aws", "google", "microsoft", "coursera", "udemy")
    for line in lines:
        ll = _match_normalize(line)
        if any(h in ll for h in hints):
            out.append(line.strip())
        if len(out) >= 8:
            break
    return out


def _extract_languages(lines: list[str]) -> list[str]:
    langs = []
    known = ["english", "vietnamese", "japanese", "korean", "chinese", "french", "german"]
    for line in lines:
        ll = _match_normalize(line)
        for k in known:
            if k in ll and k not in langs:
                langs.append(k)
    return langs[:6]

def _extract_summary(paragraphs: list[str]) -> str | None:
    for p in paragraphs[:8]:
        cleaned = p.strip()
        if len(cleaned) < 50:
            continue
        lc = _match_normalize(cleaned)
        if any(k in lc for k in ("email", "phone", "linkedin", "github", "thong tin lien he")):
            continue
        return cleaned[:700]
    return None


def _field_confidence(value: Any, mode: str = "text") -> str:
    if mode == "list":
        size = len(value or [])
        if size >= 3:
            return "high"
        if size >= 1:
            return "medium"
        return "low"

    if mode == "int":
        if value is None:
            return "low"
        if isinstance(value, int) and value >= 1:
            return "high"
        return "medium"

    text = (value or "").strip() if isinstance(value, str) else ""
    if len(text) >= 20:
        return "high"
    if len(text) >= 5:
        return "medium"
    return "low"


def parse_candidate_from_cv(text: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    lines = [ln.strip() for ln in normalized.split("\n") if ln.strip()]
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]

    result = {
        "name": _extract_name(lines),
        "email": _extract_email(normalized),
        "phone": _extract_phone(normalized),
        "skills": _extract_skills(normalized),
        "years_of_experience": _extract_years_of_experience(normalized),
        "education": _extract_education(lines),
        "previous_companies": _extract_previous_companies(lines),
        "summary": _extract_summary(paragraphs),
        "linkedin_url": _extract_linkedin(normalized),
        "github_url": _extract_github(normalized),
        "location": _extract_location(lines),
        "current_title": _extract_headline(lines),
        "certifications": _extract_certifications(lines),
        "languages": _extract_languages(lines),
        "source": "rule_based_vn_en",
    }

    confidence = {
        "name": _field_confidence(result["name"]),
        "email": "high" if result["email"] else "low",
        "phone": "high" if result["phone"] else "low",
        "skills": _field_confidence(result["skills"], "list"),
        "years_of_experience": _field_confidence(result["years_of_experience"], "int"),
        "education": _field_confidence(result["education"], "list"),
        "previous_companies": _field_confidence(result["previous_companies"], "list"),
        "summary": _field_confidence(result["summary"]),
        "linkedin_url": "high" if result.get("linkedin_url") else "low",
        "github_url": "high" if result.get("github_url") else "low",
        "location": _field_confidence(result.get("location")),
        "current_title": _field_confidence(result.get("current_title")),
        "certifications": _field_confidence(result.get("certifications"), "list"),
        "languages": _field_confidence(result.get("languages"), "list"),
        "projects": _field_confidence(result.get("projects"), "list"),
    }
    score_map = {"low": 0, "medium": 0.6, "high": 1.0}
    overall = int(round(sum(score_map[c] for c in confidence.values()) / len(confidence) * 100))

    result["confidence"] = confidence
    result["confidence_score"] = overall
    return result




TITLE_ALIASES: dict[str, list[str]] = {
    "software engineer": ["software engineer", "software developer", "swe", "developer"],
    "backend engineer": ["backend engineer", "backend developer", "server-side engineer", "back-end engineer"],
    "frontend engineer": ["frontend engineer", "front-end engineer", "frontend developer", "front-end developer", "fe developer"],
    "fullstack engineer": ["fullstack engineer", "full-stack engineer", "fullstack developer", "full-stack developer"],
    "data engineer": ["data engineer", "etl engineer", "big data engineer"],
    "data analyst": ["data analyst", "bi analyst", "business intelligence analyst"],
    "data scientist": ["data scientist", "ml scientist", "machine learning scientist"],
    "devops engineer": ["devops engineer", "sre", "site reliability engineer", "platform engineer"],
    "qa engineer": ["qa engineer", "test engineer", "quality assurance engineer", "software tester"],
    "product manager": ["product manager", "pm", "product owner"],
    "project manager": ["project manager", "delivery manager"],
    "ui/ux designer": ["ui designer", "ux designer", "ui ux designer", "product designer"],
    "mobile developer": ["mobile developer", "android developer", "ios developer", "flutter developer", "react native developer"],
}


def _normalize_job_title(raw: str | None) -> str:
    t = _match_normalize(raw or "")
    if not t:
        return ""
    for canonical, aliases in TITLE_ALIASES.items():
        probes = [_match_normalize(canonical), *[_match_normalize(a) for a in aliases]]
        if t in probes:
            return canonical
        if any(p in t for p in probes):
            return canonical
    return t


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz  # optional
        return float(fuzz.token_set_ratio(a, b)) / 100.0
    except Exception:
        return SequenceMatcher(None, a, b).ratio()


def _title_similarity(job_title: str, candidate: dict[str, Any]) -> float:
    jt = _normalize_job_title(job_title)
    ct = _normalize_job_title(candidate.get("current_title") or candidate.get("title") or "")
    if not ct:
        # try infer from summary first line keywords
        ct = _normalize_job_title((candidate.get("summary") or "")[:120])
    if not jt or not ct:
        return 0.0
    return max(0.0, min(1.0, _fuzzy_ratio(jt, ct)))

def _tokenize(text: str) -> set[str]:
    norm = _match_normalize(text)
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", norm))


def _required_years(requirements: str) -> int | None:
    m = YEARS_EXPLICIT_RE.search(_match_normalize(requirements))
    return int(m.group(1)) if m else None




_EMBED_MODEL = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    model_name = getattr(settings, "matching_embedding_model", "") or "sentence-transformers/all-MiniLM-L6-v2"
    try:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer(model_name)
    except Exception:
        _EMBED_MODEL = False
    return _EMBED_MODEL


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _semantic_similarity(job_title: str, requirements: str, candidate: dict[str, Any]) -> float:
    enabled = bool(getattr(settings, "matching_enable_embeddings", False))
    if not enabled:
        return 0.0

    model = _get_embed_model()
    if not model:
        return 0.0

    job_text = "\n".join([job_title or "", requirements or ""]).strip()
    cand_text = " ".join(
        [
            candidate.get("current_title") or "",
            candidate.get("summary") or "",
            " ".join(candidate.get("skills") or []),
            " ".join(candidate.get("previous_companies") or []),
            " ".join(candidate.get("education") or []),
        ]
    ).strip()
    if not job_text or not cand_text:
        return 0.0

    try:
        emb = model.encode([job_text, cand_text], normalize_embeddings=False)
        v1 = list(map(float, emb[0]))
        v2 = list(map(float, emb[1]))
        return _cosine(v1, v2)
    except Exception:
        return 0.0

def match_candidate_rule_based(job_title: str, requirements: str, candidate: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    req_text = f"{job_title}\n{requirements}"

    required_skills = set(_extract_skills(req_text))
    candidate_skills = set((candidate.get("skills") or []))

    if required_skills:
        overlap = required_skills.intersection(candidate_skills)
        skill_score = len(overlap) / len(required_skills)
    else:
        overlap = set()
        skill_score = 0.5

    req_years = _required_years(requirements)
    title_score = _title_similarity(job_title, candidate)
    semantic_score = _semantic_similarity(job_title, requirements, candidate)
    cand_years = candidate.get("years_of_experience") or 0
    if req_years is None:
        exp_score = 0.6 if cand_years else 0.35
    else:
        exp_score = min(1.0, cand_years / max(1, req_years))

    candidate_text = " ".join(
        [
            candidate.get("summary") or "",
            " ".join(candidate.get("education") or []),
            " ".join(candidate.get("previous_companies") or []),
            " ".join(candidate.get("skills") or []),
        ]
    )
    req_tokens = _tokenize(req_text)
    cand_tokens = _tokenize(candidate_text)
    kw_overlap = len(req_tokens.intersection(cand_tokens))
    kw_score = kw_overlap / max(1, min(100, len(req_tokens)))

    final_score = int(round((skill_score * 0.40 + exp_score * 0.18 + title_score * 0.17 + kw_score * 0.10 + semantic_score * 0.15) * 100))
    final_score = max(0, min(100, final_score))

    matched_skills = sorted(overlap)
    missing_skills = sorted(required_skills - overlap) if required_skills else []

    if str(lang).lower().startswith("vi"):
        explanation_lines = [
            f"Điểm phù hợp tổng thể: {final_score}%.",
            f"Mức độ phù hợp kỹ năng: khớp {len(matched_skills)}/{len(required_skills) if required_skills else 0} kỹ năng bắt buộc ({', '.join(matched_skills[:8]) if matched_skills else 'không có kỹ năng bắt buộc cụ thể'}).",
            f"Đánh giá kinh nghiệm: ứng viên có {cand_years} năm" + (f", yêu cầu là {req_years} năm." if req_years is not None else ", chưa có mức tối thiểu cố định.") + f" Điểm thành phần kinh nghiệm: {round(exp_score * 100)}%.",
            f"Mức độ phù hợp chức danh: {round(title_score * 100)}% (job title so với current title).",
            f"Mức độ liên quan chức danh/ngữ nghĩa: {round(semantic_score * 100)}% (embedding).",
            f"Mức độ liên quan ngữ cảnh: trùng {kw_overlap} từ khóa, điểm thành phần từ khóa: {round(kw_score * 100)}%.",
            f"Khoảng trống chính: {', '.join(missing_skills[:8]) if missing_skills else 'không có khoảng trống kỹ năng bắt buộc đáng kể'}.",
        ]
    else:
        explanation_lines = [
            f"Overall match score: {final_score}%.",
            f"Skills fit: matched {len(matched_skills)}/{len(required_skills) if required_skills else 0} required skills ({', '.join(matched_skills[:8]) if matched_skills else 'none explicitly required'}).",
            f"Experience check: candidate has {cand_years} year(s)" + (f", requirement is {req_years} year(s)." if req_years is not None else ", no strict minimum set.") + f" Experience component score: {round(exp_score * 100)}%.",
            f"Title similarity: {round(title_score * 100)}% (job title vs candidate title).",
            f"Semantic relevance: {round(semantic_score * 100)}% (embedding similarity).",
            f"Context relevance: keyword overlap {kw_overlap} term(s), keyword component score: {round(kw_score * 100)}%.",
            f"Main gaps: {', '.join(missing_skills[:8]) if missing_skills else 'no major required-skill gaps detected'}.",
        ]

    explanation = "\n".join(explanation_lines)
    return {
        "match_score": final_score,
        "explanation": explanation,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "required_skills": sorted(required_skills),
        "skill_score_pct": round(skill_score * 100, 2),
        "experience_score_pct": round(exp_score * 100, 2),
        "keyword_score_pct": round(kw_score * 100, 2),
        "title_score_pct": round(title_score * 100, 2),
        "semantic_score_pct": round(semantic_score * 100, 2),
    }



def _extract_domain_tags(text: str) -> list[str]:
    t = _match_normalize(text)
    tags = []
    hints = {
        "fintech": ["fintech", "bank", "payment", "e-wallet"],
        "ecommerce": ["ecommerce", "e-commerce", "marketplace", "shop"],
        "saas": ["saas", "b2b", "subscription"],
        "healthcare": ["healthcare", "hospital", "medical"],
        "education": ["edtech", "education", "learning"],
        "logistics": ["logistics", "supply chain", "warehouse"],
        "ai/ml": ["machine learning", "deep learning", "ai", "llm"],
    }
    for k, arr in hints.items():
        if any(x in t for x in arr):
            tags.append(k)
    return tags[:6]


def _extract_notice_period(text: str) -> str | None:
    t = _normalize_text(text)
    m = re.search(r"(notice\s*period|available\s*from|can\s*join)[:\s-]*([^\n]{2,40})", t, re.I)
    return m.group(2).strip() if m else None


def _extract_preferred_location(text: str) -> str | None:
    t = _normalize_text(text)
    m = re.search(r"(preferred\s*location|location\s*preference|willing\s*to\s*relocate)[:\s-]*([^\n]{2,60})", t, re.I)
    return m.group(2).strip() if m else None




def _extract_experience_timeline(lines: list[str]) -> list[dict[str, str]]:
    timeline = []
    date_re = re.compile(r"(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|present|now)", re.I)
    for i, ln in enumerate(lines[:220]):
        m = date_re.search(ln)
        if not m:
            continue
        role = ln.strip()
        company = lines[i - 1].strip() if i > 0 else ""
        if len(company) < 3:
            company = ""
        timeline.append(
            {
                "role": role[:120],
                "company": company[:120],
                "period": m.group(0),
            }
        )
    return timeline[:12]
