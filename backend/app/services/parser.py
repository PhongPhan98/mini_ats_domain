from io import BytesIO
from pathlib import Path
import re

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
        candidates = [
            CVTextParser._parse_pdf_with_pypdf(content),
            CVTextParser._parse_pdf_with_pdfplumber(content),
        ]
        text = max(candidates, key=CVTextParser._text_quality_score)
        if CVTextParser._is_strong_text(text):
            return text

        text_ocr = CVTextParser._parse_pdf_with_ocr(content)
        if CVTextParser._text_quality_score(text_ocr) > CVTextParser._text_quality_score(text):
            text = text_ocr
        return text.strip()

    @staticmethod
    def _parse_pdf_with_pypdf(content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            pages = []
            for page in reader.pages:
                try:
                    text = page.extract_text(extraction_mode="layout") or ""
                except TypeError:
                    text = page.extract_text() or ""
                pages.append(text)
            return CVTextParser._clean_extracted_text("\n\n".join(pages))
        except Exception:
            return ""

    @staticmethod
    def _parse_pdf_with_pdfplumber(content: bytes) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(BytesIO(content)) as pdf:
                pages = [
                    p.extract_text(x_tolerance=2, y_tolerance=3, layout=True) or ""
                    for p in pdf.pages
                ]
            return CVTextParser._clean_extracted_text("\n\n".join(pages))
        except Exception:
            return ""

    @staticmethod
    def _parse_pdf_with_ocr(content: bytes) -> str:
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            images = convert_from_bytes(content, dpi=250, first_page=1, last_page=25)
            chunks = []
            for img in images:
                txt = pytesseract.image_to_string(img, lang="eng+vie")
                if txt:
                    chunks.append(txt)
            return CVTextParser._clean_extracted_text("\n\n".join(chunks))
        except Exception:
            return ""

    @staticmethod
    def _is_strong_text(text: str) -> bool:
        text = (text or "").strip()
        return len(text) >= 180 and len(re.findall(r"\b\w{2,}\b", text)) >= 30

    @staticmethod
    def _text_quality_score(text: str) -> float:
        text = (text or "").strip()
        if not text:
            return 0
        words = re.findall(r"\b\w{2,}\b", text)
        readable = sum(ch.isalnum() or ch.isspace() or ch in "@+.,:/()#&%-" for ch in text)
        readable_ratio = readable / max(1, len(text))
        unique_ratio = len({word.lower() for word in words}) / max(1, len(words))
        return min(len(words), 2500) + min(text.count("\n"), 150) + readable_ratio * 100 + unique_ratio * 30

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        try:
            doc = Document(BytesIO(content))
        except Exception:
            return ""

        chunks: list[str] = []
        chunks.extend(p.text for p in doc.paragraphs if p.text.strip())

        # CV templates frequently place contact, skills and education in tables.
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    chunks.append(" | ".join(dict.fromkeys(cells)))

        # Headers and footers often contain contact details.
        for section in doc.sections:
            for area in (section.header, section.footer):
                chunks.extend(p.text for p in area.paragraphs if p.text.strip())

        # Preserve hyperlink targets when the visible label is only "LinkedIn".
        for relationship in doc.part.rels.values():
            target = str(getattr(relationship, "target_ref", "") or "")
            if target.lower().startswith(("http://", "https://")):
                chunks.append(target)

        return CVTextParser._clean_extracted_text("\n".join(chunks))

    @staticmethod
    def _clean_extracted_text(text: str) -> str:
        text = (text or "").replace("\x00", "").replace("\u00a0", " ")
        text = text.replace("\u200b", "").replace("\ufeff", "")
        lines = []
        previous = None
        for raw in text.replace("\r", "\n").split("\n"):
            line = " ".join(raw.split()).strip()
            if not line:
                if lines and lines[-1] != "":
                    lines.append("")
                continue
            if line == previous:
                continue
            lines.append(line)
            previous = line
        return "\n".join(lines).strip()
