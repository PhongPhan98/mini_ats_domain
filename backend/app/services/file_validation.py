import io
import zipfile
from pathlib import Path


MAX_CV_BYTES = 20 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


def validate_cv_file(filename: str, content: bytes) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise ValueError("Only PDF and DOCX files are supported")
    if not content:
        raise ValueError("The CV file is empty")
    if len(content) > MAX_CV_BYTES:
        raise OverflowError("CV file must be 20 MB or smaller")
    if suffix == ".pdf":
        if not content.lstrip()[:5] == b"%PDF-":
            raise ValueError("The file does not contain a valid PDF")
        return
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if "word/document.xml" not in {member.filename for member in members}:
                raise ValueError("The file does not contain a valid Word document")
            if sum(member.file_size for member in members) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ValueError("The Word document expands beyond the safe processing limit")
            if any(member.compress_size and member.file_size / member.compress_size > 200 for member in members):
                raise ValueError("The Word document has an unsafe compression ratio")
    except zipfile.BadZipFile as exc:
        raise ValueError("The file does not contain a valid DOCX document") from exc
