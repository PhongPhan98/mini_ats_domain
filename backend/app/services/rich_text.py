"""Small allowlist sanitizer for candidate profile rich text."""
from html import escape
from html.parser import HTMLParser
import re
from typing import Any


RICH_TEXT_FIELDS = {"summary", "education", "experience_details", "achievements"}
ALLOWED_TAGS = {"p", "div", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "h2", "h3", "span"}
COLOR_RE = re.compile(r"(?:#[0-9a-f]{3,8}|rgba?\([\d\s,.%]+\)|yellow|transparent)\Z", re.I)


def _safe_style(raw: str) -> str:
    output = []
    for declaration in raw.split(";"):
        if ":" not in declaration:
            continue
        prop, value = (part.strip().lower() for part in declaration.split(":", 1))
        if prop in {"background-color", "color"} and COLOR_RE.fullmatch(value):
            output.append(f"{prop}: {value}")
        elif prop == "text-align" and value in {"left", "center", "right"}:
            output.append(f"{prop}: {value}")
    return "; ".join(output)


class _RichTextCleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object"}:
            self.suppressed += 1
            return
        if self.suppressed or tag not in ALLOWED_TAGS:
            return
        style = _safe_style(dict(attrs).get("style") or "")
        style_attr = f' style="{escape(style, quote=True)}"' if style else ""
        self.output.append(f"<{tag}{style_attr}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br" and not self.suppressed:
            self.output.append("<br>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object"} and self.suppressed:
            self.suppressed -= 1
            return
        if not self.suppressed and tag in ALLOWED_TAGS and tag != "br":
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            self.output.append(escape(data))


def sanitize_rich_html(value: str) -> str:
    cleaner = _RichTextCleaner()
    cleaner.feed(value[:100_000])
    cleaner.close()
    return "".join(cleaner.output)[:50_000]


def clean_rich_text(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        field: cleaned
        for field, raw in value.items()
        if field in RICH_TEXT_FIELDS and isinstance(raw, str) and (cleaned := sanitize_rich_html(raw))
    }
