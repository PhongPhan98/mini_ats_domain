"""Deterministic CV field and date extraction for English and Vietnamese CVs."""
import re
import unicodedata
from datetime import datetime


def normalize(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn").replace("đ", "d")


PREFERENCE_LABELS = (
    r"preferred\s+(?:work\s+)?(?:locations?|cities?|workplace)",
    r"(?:work\s+)?location\s+preferences?", r"desired\s+(?:work\s+)?location",
    r"willing\s+to\s+relocate(?:\s+to)?", r"open\s+to\s+relocat(?:ion|ing)(?:\s+to)?",
    r"(?:dia\s+diem|noi|khu\s+vuc)\s+(?:lam\s+viec\s+)?(?:mong\s+muon|uu\s+tien)",
    r"(?:mong\s+muon|uu\s+tien)\s+lam\s+viec(?:\s+tai|\s+o)?",
    r"san\s+sang\s+(?:chuyen\s+den|chuyen\s+noi\s+lam\s+viec|di\s+chuyen)(?:\s+den)?",
)
NOTICE_LABELS = (
    r"notice\s*(?:period|duration)", r"availability(?:\s+date)?", r"available\s+(?:from|after|in|to\s+(?:start|join))",
    r"(?:can|able\s+to|ready\s+to)\s+(?:start|join)(?:\s+(?:in|after|from))?",
    r"(?:earliest\s+)?(?:start|joining)\s+date",
    r"thoi\s+gian\s+(?:bao\s+truoc|nhan\s+viec|bat\s+dau)",
    r"(?:co\s+the|san\s+sang)\s+(?:nhan\s+viec|bat\s+dau)(?:\s+(?:sau|tu))?",
    r"ngay\s+(?:nhan\s+viec|bat\s+dau)(?:\s+du\s+kien)?",
)


def _labelled_value(text: str, labels: tuple[str, ...]) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pattern = re.compile(r"(?:^|\b)(?:" + "|".join(labels) + r")\b\s*[:=\-–—|]?\s*", re.I)
    other_labels = re.compile(r"\b(?:" + "|".join(PREFERENCE_LABELS + NOTICE_LABELS) + r")\b", re.I)
    for index, line in enumerate(lines):
        normalized = normalize(line)
        match = pattern.search(normalized)
        if not match:
            continue
        # Truncate at table-cell separators or the next labelled field.
        value = line[match.end():].strip(" :|=-–—")
        next_label = other_labels.search(normalize(value))
        if next_label:
            value = value[:next_label.start()].strip(" :|;=-–—")
        value = value.split("|")[0].strip()
        if not value and index + 1 < len(lines):
            following = lines[index + 1]
            headings = {"work experience", "experience", "education", "skills", "projects", "languages", "certifications", "kinh nghiem", "hoc van", "ky nang"}
            if normalize(following).strip(" :") not in headings and not other_labels.search(normalize(following)) and not re.search(r"[:=]", following):
                value = following.strip(" :|=-–—")
        if value and normalize(value) not in {"n/a", "na", "unknown", "not stated", "khong ro"}:
            return value[:160]
    return None


def preferred_location(text: str) -> str | None:
    return _labelled_value(text, PREFERENCE_LABELS)


def is_preference_line(line: str) -> bool:
    return bool(re.search(r"\b(?:" + "|".join(PREFERENCE_LABELS + NOTICE_LABELS) + r")\b", normalize(line)))


def notice_period(text: str) -> str | None:
    value = _labelled_value(text, NOTICE_LABELS)
    if value:
        return value
    duration = re.search(r"\b(\d{1,3}\s+(?:business\s+)?(?:days?|weeks?|months?|ngay|tuan|thang))\s+(?:of\s+)?notice\b", normalize(text))
    if duration:
        return text[duration.start(1):duration.end(1)].strip()
    immediate = re.search(r"\b(?:immediately\s+available|available\s+immediately|immediate\s+availability|join\s+immediately|nhan\s+viec\s+ngay|bat\s+dau\s+ngay)\b", normalize(text))
    return "Immediately" if immediate else None


MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_NAME = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
YEAR = r"(?:19|20)\d{2}"
DATE_TOKEN = rf"(?:{YEAR}[/.-](?:0?[1-9]|1[0-2])\b|(?:0?[1-9]|1[0-2])[/.-]{YEAR}|{MONTH_NAME}\s+{YEAR}|thang\s+\d{{1,2}}\s*[/.,-]?\s*{YEAR}|{YEAR})"
PERIOD_RE = re.compile(rf"(?P<start>{DATE_TOKEN})\s*(?:[-–—]|\bto\b|\bden\b)\s*(?P<end>present|current|now|today|nay|hien\s*tai|{DATE_TOKEN})", re.I)


def _month_index(value: str, *, end: bool = False) -> int | None:
    current = datetime.now()
    value = normalize(value).strip()
    if value in {"present", "current", "now", "today", "nay", "hien tai"}:
        return current.year * 12 + current.month - 1
    year_match = re.search(YEAR, value)
    if not year_match:
        return None
    year = int(year_match.group())
    if year < 1980 or year > current.year:
        return None
    month = 1
    named = re.match(MONTH_NAME, value)
    before = value[:year_match.start()].strip(" /.-")
    after = value[year_match.end():].strip(" /.-")
    if named:
        month = MONTH_NAMES[named.group()[:3]]
    elif before:
        numbers = re.findall(r"\d+", before)
        if numbers:
            month = int(numbers[-1])
    elif after.isdigit():
        month = int(after)
    if not 1 <= month <= 12:
        return None
    index = year * 12 + month - 1
    return index + (1 if end and (before or after) else 0)


def employment_months(text: str) -> int | None:
    intervals = []
    now = datetime.now()
    current_month = now.year * 12 + now.month - 1
    for match in PERIOD_RE.finditer(normalize(text)):
        start = _month_index(match.group("start"))
        end = _month_index(match.group("end"), end=True)
        if start is not None and end is not None:
            end = min(end, current_month)
            if start <= end:
                intervals.append((start, end))
    if not intervals:
        return None
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)
