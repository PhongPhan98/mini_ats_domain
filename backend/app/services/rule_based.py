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

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "profile", "professional summary", "about me", "objective", "career objective", "tom tat", "gioi thieu", "muc tieu nghe nghiep"),
    "experience": ("experience", "work experience", "employment", "employment history", "professional experience", "career history", "kinh nghiem", "kinh nghiem lam viec", "qua trinh cong tac"),
    "education": ("education", "academic background", "academic history", "qualifications", "hoc van", "qua trinh hoc tap"),
    "skills": ("skills", "technical skills", "core skills", "competencies", "expertise", "tech stack", "ky nang", "ky nang chuyen mon"),
    "projects": ("projects", "selected projects", "personal projects", "key projects", "du an", "du an tieu bieu"),
    "certifications": ("certifications", "certificates", "licenses", "credentials", "chung chi", "chung nhan"),
    "languages": ("languages", "language proficiency", "ngoai ngu", "ngon ngu"),
    "achievements": ("achievements", "awards", "honors", "accomplishments", "thanh tich", "giai thuong"),
    "interests": ("interests", "hobbies", "so thich"),
    "contact": ("contact", "contact information", "personal information", "thong tin lien he", "thong tin ca nhan"),
}
SECTION_HEADER_HINTS = {alias for aliases in SECTION_ALIASES.values() for alias in aliases}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in/)?[^\s|,;]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[^\s|,;]+", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s|,;]+", re.IGNORECASE)
YEARS_EXPLICIT_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:years?|yrs?|nam)\s*(?:of\s+)?(?:experience|kinh\s*nghiem)?",
    re.IGNORECASE,
)
DATE_RANGE_RE = re.compile(
    r"(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|thang\s*\d{1,2})[\s./-]*)?"
    r"((?:19|20)\d{2})\s*(?:-|–|—|to|den)\s*"
    r"(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|thang\s*\d{1,2})[\s./-]*)?"
    r"(present|current|now|today|nay|hien\s*tai|(?:19|20)\d{2})",
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
    text = (text or "").replace("\r", "\n").replace("\u00a0", " ")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("•", "- ").replace("▪", "- ").replace("●", "- ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _looks_like_section_header(line: str) -> bool:
    compact = _match_normalize(line).strip(":|-/ ")
    return compact in SECTION_HEADER_HINTS






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
    def detect(line: str) -> str | None:
        lm = _match_normalize(line).strip(":|-/ ")
        if len(lm) > 45 or len(lm.split()) > 6:
            return None
        for key, aliases in SECTION_ALIASES.items():
            if lm in aliases:
                return key
        return None

    sections: dict[str, list[str]] = {k: [] for k in SECTION_ALIASES}
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


def _extract_years_of_experience(text: str, experience_text: str | None = None) -> int | None:
    normalized = _match_normalize(text)
    explicit = [int(x) for x in YEARS_EXPLICIT_RE.findall(normalized)]
    if explicit:
        return max(0, min(50, max(explicit)))

    current_year = datetime.now().year
    intervals: list[tuple[int, int]] = []
    range_source = _match_normalize(experience_text or text)
    for start, end in DATE_RANGE_RE.findall(range_source):
        s = int(start)
        e = current_year if end.lower() in {"present", "current", "now", "today", "nay", "hien tai"} else int(end)
        if 1980 <= s <= current_year and s <= e <= current_year:
            intervals.append((s, e))

    if not intervals:
        return None

    # Merge overlapping roles so concurrent jobs are not counted twice.
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    total = sum(max(0, end - start) for start, end in merged)
    return max(0, min(50, total))


def _extract_education(lines: list[str]) -> list[str]:
    edu_keys = (
        "university", "college", "bachelor", "master", "phd", "doctorate", "diploma",
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
    if not m:
        return None
    value = m.group(0).strip().rstrip(".)]")
    return value if value.lower().startswith("http") else f"https://{value}"


def _extract_github(text: str) -> str | None:
    m = GITHUB_RE.search(text)
    if not m:
        return None
    value = m.group(0).strip().rstrip(".)]")
    return value if value.lower().startswith("http") else f"https://{value}"


def _extract_location(lines: list[str]) -> str | None:
    label_re = re.compile(r"^(?:location|address|dia chi|noi o)\s*[:|-]\s*(.+)$", re.I)
    hints = ("ho chi minh", "hanoi", "da nang", "vietnam", "tp.hcm", "ha noi", "remote", "can tho", "hai phong", "singapore", "bangkok")
    for line in lines[:20]:
        labelled = label_re.match(line.strip())
        if labelled:
            return labelled.group(1).strip()[:120]
        ll = _match_normalize(line)
        if any(h in ll for h in hints):
            return line.strip()[:120]
    return None


def _extract_headline(lines: list[str]) -> str | None:
    role_hints = ("developer", "engineer", "designer", "tester", "qa", "data", "product", "manager", "devops", "frontend", "backend", "fullstack", "analyst", "architect", "consultant", "recruiter", "accountant", "marketing", "sales", "director", "specialist", "lead")
    for line in lines[:15]:
        ll = _match_normalize(line)
        if any(h in ll for h in role_hints) and len(line.strip()) <= 120 and not _looks_like_section_header(line):
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


def _dedupe_values(values: list[Any], max_items: int = 20) -> list[Any]:
    output: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value in (None, "", [], {}):
            continue
        key = _match_normalize(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value))
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
        if len(output) >= max_items:
            break
    return output


def _extract_section_summary(lines: list[str]) -> str | None:
    clean = _clean_lines(lines, min_len=12, max_items=5)
    if not clean:
        return None
    return " ".join(clean)[:1000]


def _extract_section_skills(lines: list[str]) -> list[str]:
    found: list[str] = []
    alias_lookup = {
        _match_normalize(alias): canonical
        for canonical, aliases in SKILL_ALIASES.items()
        for alias in [canonical, *aliases]
    }
    for raw in lines[:50]:
        value = re.sub(r"^(?:technical\s+)?skills?\s*[:|-]\s*", "", raw, flags=re.I)
        for item in re.split(r"[,;|/]|\s+-\s+", value):
            item = item.strip(" -*•\t:.")
            normalized = _match_normalize(item)
            if not normalized or len(item) > 45 or len(item.split()) > 5:
                continue
            if normalized in SECTION_HEADER_HINTS or re.search(r"\b(?:19|20)\d{2}\b", item):
                continue
            if normalized in {"advanced", "intermediate", "beginner", "basic", "expert", "proficient"}:
                continue
            found.append(alias_lookup.get(normalized, item))
    return _dedupe_values(found, max_items=35)


def _extract_experience_details(lines: list[str]) -> list[str]:
    return _clean_lines(lines, min_len=4, max_items=30)


def _extract_experience_timeline_v2(lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    role_hints = ("engineer", "developer", "designer", "manager", "analyst", "architect", "consultant", "recruiter", "specialist", "lead", "director", "intern", "tester", "accountant", "marketing", "sales", "product", "project")
    for index, line in enumerate(lines[:240]):
        match = DATE_RANGE_RE.search(_match_normalize(line))
        if not match:
            continue

        period = match.group(0)
        header = re.sub(re.escape(period), "", line, flags=re.I).strip(" -|•")
        if not header and index > 0:
            header = lines[index - 1].strip(" -|•")

        parts = [part.strip() for part in re.split(r"\s*[|@]\s*|\s+at\s+", header, maxsplit=1, flags=re.I) if part.strip()]
        role = ""
        company = ""
        if len(parts) >= 2:
            role_part = next((part for part in parts if any(h in _match_normalize(part) for h in role_hints)), parts[0])
            role = role_part
            company = next((part for part in parts if part != role_part), "")
        elif parts:
            if any(h in _match_normalize(parts[0]) for h in role_hints):
                role = parts[0]
            else:
                company = parts[0]

        if not company and index > 1:
            candidate = lines[index - 2].strip(" -|•")
            if not DATE_RANGE_RE.search(_match_normalize(candidate)) and not any(h in _match_normalize(candidate) for h in role_hints):
                company = candidate

        highlights: list[str] = []
        for offset, following in enumerate(lines[index + 1:index + 7], start=index + 1):
            if DATE_RANGE_RE.search(_match_normalize(following)):
                break
            following_norm = _match_normalize(following)
            next_is_period = offset + 1 < len(lines) and DATE_RANGE_RE.search(_match_normalize(lines[offset + 1]))
            if next_is_period and any(h in following_norm for h in role_hints):
                break
            if len(following.strip()) >= 12:
                highlights.append(following.strip(" -|•")[:260])
            if len(highlights) >= 3:
                break

        entries.append({
            "role": role[:140] or None,
            "company": company[:140] or None,
            "period": period[:80],
            "highlights": _dedupe_values(highlights, max_items=3),
        })
    return _dedupe_values(entries, max_items=15)


def _extract_achievements(section_lines: list[str], experience_lines: list[str]) -> list[str]:
    direct = _clean_lines(section_lines, min_len=6, max_items=12)
    if direct:
        return direct
    result: list[str] = []
    impact_words = ("increased", "reduced", "improved", "grew", "saved", "achieved", "award", "winner", "tang", "giam", "cai thien", "dat duoc")
    for line in experience_lines:
        normalized = _match_normalize(line)
        if any(word in normalized for word in impact_words) and re.search(r"\d|%", line):
            result.append(line.strip(" -|•")[:280])
    return _dedupe_values(result, max_items=10)


def _extract_portfolio_urls(text: str) -> list[str]:
    ignored = ("linkedin.com", "github.com", "mailto:")
    urls = [m.group(0).rstrip(".)]") for m in URL_RE.finditer(text)]
    return _dedupe_values([url for url in urls if not any(item in url.lower() for item in ignored)], max_items=6)


def _parse_completeness(result: dict[str, Any]) -> tuple[int, list[str]]:
    weights = {
        "name": 15, "email": 15, "phone": 8, "current_title": 8,
        "skills": 14, "years_of_experience": 8, "experience_details": 10,
        "education": 7, "summary": 7, "location": 4, "previous_companies": 4,
    }
    score = sum(weight for field, weight in weights.items() if result.get(field) not in (None, "", [], {}))
    missing = [field for field in ("name", "email", "phone", "skills", "current_title", "experience_details") if result.get(field) in (None, "", [], {})]
    return min(100, score), missing


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
    sections = _extract_sections(lines)

    experience_lines = sections.get("experience") or []
    education_lines = sections.get("education") or []
    project_lines = sections.get("projects") or []
    certification_lines = sections.get("certifications") or []
    language_lines = sections.get("languages") or []
    timeline = _extract_experience_timeline_v2(experience_lines or lines)

    focused_skill_text = "\n".join(
        (sections.get("skills") or [])
        + experience_lines
        + project_lines
        + (sections.get("summary") or [])
    )
    known_skills = _extract_skills(focused_skill_text or normalized)
    section_skills = _extract_section_skills(sections.get("skills") or [])
    education = _clean_lines(education_lines, min_len=4, max_items=12) if education_lines else _extract_education(lines)
    timeline_companies = [entry.get("company") for entry in timeline if entry.get("company")]
    companies = _dedupe_values(
        timeline_companies or _extract_previous_companies(experience_lines or lines),
        max_items=15,
    )
    current_title = _extract_headline(lines)
    if not current_title and timeline:
        current_title = timeline[0].get("role")

    result = {
        "name": _extract_name(lines),
        "email": _extract_email(normalized),
        "phone": _extract_phone(normalized),
        "skills": _dedupe_values(known_skills + section_skills, max_items=40),
        "years_of_experience": _extract_years_of_experience(normalized, "\n".join(experience_lines)),
        "education": education,
        "previous_companies": companies,
        "summary": _extract_section_summary(sections.get("summary") or []) or _extract_summary(paragraphs),
        "linkedin_url": _extract_linkedin(normalized),
        "github_url": _extract_github(normalized),
        "portfolio_urls": _extract_portfolio_urls(normalized),
        "location": _extract_location(lines),
        "current_title": current_title,
        "certifications": _clean_lines(certification_lines, min_len=4, max_items=12) if certification_lines else _extract_certifications(lines),
        "languages": _dedupe_values(
            [item.strip() for line in language_lines for item in re.split(r"[|;,]", line) if item.strip()]
            if language_lines else _extract_languages(lines),
            max_items=10,
        ),
        "projects": _extract_projects(project_lines),
        "experience_details": _extract_experience_details(experience_lines),
        "experience_timeline": timeline,
        "achievements": _extract_achievements(sections.get("achievements") or [], experience_lines),
        "domain_tags": _extract_domain_tags(normalized),
        "preferred_location": _extract_preferred_location(normalized),
        "notice_period": _extract_notice_period(normalized),
        "source": "rule_based_v2",
        "parser_version": "2.0",
        "text_character_count": len(normalized),
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
        "experience_details": _field_confidence(result.get("experience_details"), "list"),
        "experience_timeline": _field_confidence(result.get("experience_timeline"), "list"),
        "achievements": _field_confidence(result.get("achievements"), "list"),
        "domain_tags": _field_confidence(result.get("domain_tags"), "list"),
        "preferred_location": _field_confidence(result.get("preferred_location")),
        "notice_period": _field_confidence(result.get("notice_period")),
    }
    score_map = {"low": 0, "medium": 0.6, "high": 1.0}
    overall = int(round(sum(score_map[c] for c in confidence.values()) / len(confidence) * 100))

    result["confidence"] = confidence
    result["confidence_score"] = overall
    completeness, missing = _parse_completeness(result)
    result["completeness_score"] = completeness
    result["missing_critical_fields"] = missing
    result["review_recommended"] = bool(missing or completeness < 70)
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
        "education": ["edtech", "learning platform", "learning management system"],
        "logistics": ["logistics", "supply chain", "warehouse"],
        "ai/ml": ["machine learning", "deep learning", "ai", "llm"],
        "cybersecurity": ["cybersecurity", "information security", "soc", "penetration testing"],
        "telecommunications": ["telecom", "telecommunications", "mobile network"],
        "insurance": ["insurance", "insurtech", "underwriting"],
        "retail": ["retail", "point of sale", "pos system"],
        "gaming": ["game development", "gaming", "unity", "unreal engine"],
        "manufacturing": ["manufacturing", "factory", "production planning"],
    }
    for k, arr in hints.items():
        if any(re.search(rf"(?<![a-z0-9]){re.escape(x)}(?![a-z0-9])", t) for x in arr):
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




PARSED_LIST_FIELDS = {
    "skills", "education", "previous_companies", "certifications", "languages",
    "projects", "experience_details", "achievements", "domain_tags", "portfolio_urls",
}
PARSED_TEXT_FIELDS = {
    "name", "email", "phone", "summary", "linkedin_url", "github_url", "location",
    "current_title", "preferred_location", "notice_period",
}


def _normalize_ai_list(value: Any, max_items: int = 30) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"\n|\s*[|;]\s*", value)
    elif isinstance(value, list):
        values = value
    else:
        return []
    clean = []
    for item in values:
        if isinstance(item, dict):
            continue
        text = re.sub(r"\s+", " ", str(item or "")).strip(" -*•\t")
        if 1 < len(text) <= 500:
            clean.append(text)
    return _dedupe_values(clean, max_items=max_items)


def normalize_ai_candidate(data: dict[str, Any] | None) -> dict[str, Any]:
    """Validate model output and discard unsupported or sensitive attributes."""
    if not isinstance(data, dict):
        return {}
    clean: dict[str, Any] = {}
    for field in PARSED_TEXT_FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            value = re.sub(r"\s+", " ", value).strip()
            if value and len(value) <= (1500 if field == "summary" else 300):
                clean[field] = value

    email = clean.get("email")
    if email and not EMAIL_RE.fullmatch(email):
        clean.pop("email", None)
    phone = clean.get("phone")
    if phone:
        validated_phone = _extract_phone(phone)
        if validated_phone:
            clean["phone"] = validated_phone
        else:
            clean.pop("phone", None)
    for field in ("linkedin_url", "github_url"):
        value = clean.get(field)
        if value and not value.lower().startswith(("http://", "https://")):
            clean[field] = f"https://{value}"

    for field in PARSED_LIST_FIELDS:
        clean[field] = _normalize_ai_list(data.get(field))

    years = data.get("years_of_experience")
    try:
        if years is not None and str(years).strip() != "":
            clean["years_of_experience"] = max(0, min(50, int(round(float(years)))))
    except (TypeError, ValueError):
        pass

    timeline = data.get("experience_timeline")
    if isinstance(timeline, list):
        entries: list[dict[str, Any]] = []
        for raw in timeline[:20]:
            if not isinstance(raw, dict):
                continue
            entry = {
                "role": str(raw.get("role") or "").strip()[:140] or None,
                "company": str(raw.get("company") or "").strip()[:140] or None,
                "period": str(raw.get("period") or "").strip()[:80] or None,
                "highlights": _normalize_ai_list(raw.get("highlights"), max_items=5),
            }
            if any(entry.values()):
                entries.append(entry)
        clean["experience_timeline"] = entries
    return clean


def merge_candidate_parses(rule_data: dict[str, Any], ai_data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge deterministic evidence with validated AI enrichment."""
    parsed = dict(rule_data or {})
    ai = normalize_ai_candidate(ai_data)
    field_sources: dict[str, str] = {
        key: "local" for key, value in parsed.items() if value not in (None, "", [], {})
    }
    conflicts: list[str] = []

    # Exact-pattern contact fields win over generative output. Record disagreement
    # for human review instead of silently replacing evidence from the document.
    for field in ("email", "phone", "linkedin_url", "github_url"):
        local_value = parsed.get(field)
        ai_value = ai.get(field)
        if local_value and ai_value and _match_normalize(str(local_value)) != _match_normalize(str(ai_value)):
            conflicts.append(field)
        if not local_value and ai_value:
            parsed[field] = ai_value
            field_sources[field] = "ai"

    for field in PARSED_TEXT_FIELDS - {"email", "phone", "linkedin_url", "github_url"}:
        ai_value = ai.get(field)
        if ai_value not in (None, ""):
            parsed[field] = ai_value
            field_sources[field] = "ai"

    for field in PARSED_LIST_FIELDS:
        combined = _dedupe_values((ai.get(field) or []) + (parsed.get(field) or []), max_items=40)
        parsed[field] = combined
        if ai.get(field):
            field_sources[field] = "ai+local" if rule_data.get(field) else "ai"

    if ai.get("years_of_experience") is not None:
        parsed["years_of_experience"] = ai["years_of_experience"]
        field_sources["years_of_experience"] = "ai"
    if ai.get("experience_timeline"):
        parsed["experience_timeline"] = ai["experience_timeline"]
        field_sources["experience_timeline"] = "ai"

    confidence: dict[str, str] = {}
    for field in sorted(PARSED_TEXT_FIELDS):
        value = parsed.get(field)
        confidence[field] = "high" if field in {"email", "phone", "linkedin_url", "github_url"} and value else _field_confidence(value)
    for field in sorted(PARSED_LIST_FIELDS | {"experience_timeline"}):
        confidence[field] = _field_confidence(parsed.get(field), "list")
    confidence["years_of_experience"] = _field_confidence(parsed.get("years_of_experience"), "int")

    score_map = {"low": 0, "medium": 0.6, "high": 1.0}
    parsed["confidence"] = confidence
    parsed["confidence_score"] = int(round(sum(score_map[x] for x in confidence.values()) / max(1, len(confidence)) * 100))
    completeness, missing = _parse_completeness(parsed)
    parsed["completeness_score"] = completeness
    parsed["missing_critical_fields"] = missing
    parsed["review_recommended"] = bool(missing or conflicts or completeness < 70)
    parsed["field_sources"] = field_sources
    parsed["parse_conflicts"] = conflicts
    parsed["parser_version"] = "2.0"
    return parsed
