from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


class CVTextParser:
    @staticmethod
    def parse(filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return CVTextParser._parse_pdf(content)
        if suffix == ".docx":
            return CVTextParser._parse_docx(content)
        raise ValueError("Only PDF and DOCX are supported")

    @staticmethod
    def _parse_pdf(content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        doc = Document(BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
