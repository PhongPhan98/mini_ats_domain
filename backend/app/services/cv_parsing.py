"""One local parsing entry point shared by preview and CV imports."""
from pathlib import Path
from typing import Any

from app.services.parser import CVTextParser
from app.services.rule_based import parse_candidate_from_cv
from app.services.rich_text import clean_rich_text

TEXT_FIELDS = {
    "name", "email", "phone", "summary", "current_title", "location",
    "linkedin_url", "github_url", "preferred_location", "notice_period",
}
LIST_FIELDS = {
    "skills", "education", "previous_companies", "certifications", "languages",
    "projects", "experience_details", "achievements", "domain_tags", "portfolio_urls",
}
METADATA_FIELDS = {
    "confidence", "confidence_score", "completeness_score", "missing_critical_fields",
    "review_recommended", "field_sources", "field_evidence", "parser_version",
    "parse_warning", "scanned_suspected", "experience_timeline", "text_character_count",
    "experience_months", "experience_calculation",
}


def clean_reviewed_profile(data: dict[str, Any]) -> dict[str, Any]:
    """Keep extracted facts and reviewed values, excluding old provider metadata."""
    clean = {key: value for key, value in data.items() if key in METADATA_FIELDS}
    for field in TEXT_FIELDS:
        value = data.get(field)
        clean[field] = value.strip() or None if isinstance(value, str) else None
    for field in LIST_FIELDS:
        values = data.get(field)
        clean[field] = list(dict.fromkeys(item.strip() for item in values if isinstance(item, str) and item.strip())) if isinstance(values, list) else []
    years = data.get("years_of_experience")
    clean["years_of_experience"] = max(0, min(50, int(years))) if isinstance(years, (int, float)) and not isinstance(years, bool) else None
    clean["rich_text"] = clean_rich_text(data.get("rich_text"))
    clean["source"] = "local_cv_parser"
    return clean


def parse_cv_document(filename: str, content: bytes) -> tuple[dict[str, Any], str]:
    text = CVTextParser.parse(filename, content)
    parsed = parse_candidate_from_cv(text)
    parsed["source"] = "local_cv_parser"
    if not text.strip():
        parsed["suggested_name"] = Path(filename).stem.replace("_", " ").replace("-", " ")
        parsed["parse_warning"] = "No readable text was found. Review the original CV; scanned PDFs need local OCR tools."
        parsed["scanned_suspected"] = True
        parsed["review_recommended"] = True
    elif len(text.strip()) < 160:
        parsed["parse_warning"] = "Only a little text could be read. Check the original CV and review the extracted fields."
        parsed["scanned_suspected"] = True
        parsed["review_recommended"] = True
    return parsed, text
