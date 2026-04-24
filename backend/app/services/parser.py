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
        text = CVTextParser._parse_pdf_with_pypdf(content)
        if CVTextParser._is_strong_text(text):
            return text

        text_plumber = CVTextParser._parse_pdf_with_pdfplumber(content)
        if len(text_plumber) > len(text):
            text = text_plumber
        if CVTextParser._is_strong_text(text):
            return text

        text_ocr = CVTextParser._parse_pdf_with_ocr(content)
        if len(text_ocr) > len(text):
            text = text_ocr
        return text.strip()

    @staticmethod
    def _parse_pdf_with_pypdf(content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except Exception:
            return ""

    @staticmethod
    def _parse_pdf_with_pdfplumber(content: bytes) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(BytesIO(content)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages).strip()
        except Exception:
            return ""

    @staticmethod
    def _parse_pdf_with_ocr(content: bytes) -> str:
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            images = convert_from_bytes(content, dpi=250)
            chunks = []
            for img in images:
                txt = pytesseract.image_to_string(img, lang="eng+vie")
                if txt:
                    chunks.append(txt)
            return "\n".join(chunks).strip()
        except Exception:
            return ""

    @staticmethod
    def _is_strong_text(text: str) -> bool:
        return len((text or "").strip()) >= 180

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        doc = Document(BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
