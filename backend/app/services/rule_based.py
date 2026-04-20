import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

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
    }
    score_map = {"low": 0, "medium": 0.6, "high": 1.0}
    overall = int(round(sum(score_map[c] for c in confidence.values()) / len(confidence) * 100))

    result["confidence"] = confidence
    result["confidence_score"] = overall
    return result


def _tokenize(text: str) -> set[str]:
    norm = _match_normalize(text)
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", norm))


def _required_years(requirements: str) -> int | None:
    m = YEARS_EXPLICIT_RE.search(_match_normalize(requirements))
    return int(m.group(1)) if m else None


def match_candidate_rule_based(job_title: str, requirements: str, candidate: dict[str, Any]) -> dict[str, Any]:
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

    final_score = int(round((skill_score * 0.62 + exp_score * 0.25 + kw_score * 0.13) * 100))
    final_score = max(0, min(100, final_score))

    explanation = (
        f"Rule-based match: {len(overlap)} skill overlap"
        f"/{len(required_skills) if required_skills else 0}, "
        f"experience {cand_years}y"
        f"{' vs required ' + str(req_years) + 'y' if req_years is not None else ''}, "
        f"keyword overlap {kw_overlap}."
    )

    return {
        "match_score": final_score,
        "explanation": explanation,
        "matched_skills": sorted(overlap),
        "required_skills": sorted(required_skills),
    }
