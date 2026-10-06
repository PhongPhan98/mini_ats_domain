from io import BytesIO
from pathlib import Path
import re

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
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
        # Evaluate each page. A readable first page must not hide scanned pages
        # later in a mixed PDF document.
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted and not reader.decrypt(""):
                return ""
        except Exception:
            return ""

        plumber = None
        try:
            import pdfplumber
            plumber = pdfplumber.open(BytesIO(content))
        except Exception:
            pass
        pages = []
        try:
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    regular = page.extract_text() or ""
                    layout = page.extract_text(extraction_mode="layout") or ""
                except Exception:
                    regular = layout = ""
                choices = [regular, layout]
                if plumber:
                    try:
                        choices.append(plumber.pages[page_number - 1].extract_text(x_tolerance=2, y_tolerance=3) or "")
                    except Exception:
                        pass
                text = max(choices, key=CVTextParser._text_quality_score)
                if not CVTextParser._is_strong_text(text):
                    text_ocr = CVTextParser._parse_pdf_with_ocr(content, page_number)
                    if CVTextParser._text_quality_score(text_ocr) > CVTextParser._text_quality_score(text):
                        text = text_ocr
                pages.append(text)
                # Some templates show labels but put the actual link in an annotation.
                for reference in page.get("/Annots") or []:
                    try:
                        annotation = reference.get_object()
                        action = annotation.get("/A")
                        uri = str(action.get("/URI") or "") if action else ""
                        if uri.lower().startswith(("https://", "http://")):
                            pages.append(uri)
                    except Exception:
                        pass
        finally:
            if plumber:
                plumber.close()
        return CVTextParser._clean_extracted_text("\n\n".join(pages))

    @staticmethod
    def _parse_pdf_with_ocr(content: bytes, page_number: int = 1) -> str:
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            images = convert_from_bytes(content, dpi=250, first_page=page_number, last_page=page_number, timeout=20)
            chunks = []
            for img in images:
                try:
                    txt = pytesseract.image_to_string(img, lang="eng+vie", timeout=20)
                except pytesseract.TesseractError:
                    txt = pytesseract.image_to_string(img, lang="eng", timeout=20)
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
        # Preserve document order: appending all tables after paragraphs can put
        # an experience table under the education or skills heading.
        def read_blocks(parent, elements):
            for element in elements:
                if element.tag == qn("w:p"):
                    value = Paragraph(element, parent).text.strip()
                    if value:
                        chunks.append(value)
                elif element.tag == qn("w:tbl"):
                    table = Table(element, parent)
                    seen_cells = set()
                    for row in table.rows:
                        for cell in row.cells:
                            if cell._tc in seen_cells:
                                continue
                            seen_cells.add(cell._tc)
                            read_blocks(cell, cell._tc.iterchildren())

        read_blocks(doc, doc.element.body.iterchildren())

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
