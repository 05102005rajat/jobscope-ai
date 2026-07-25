from PyPDF2 import PdfReader
from app.utils.jd_parser import extract_jd_skills
import io


class InvalidPDFError(ValueError):
    """Raised when the uploaded file isn't a readable PDF."""


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as exc:
        # PyPDF2 can raise several different exception types (PdfReadError,
        # struct.error, etc.) on corrupted/encrypted/non-PDF input. Treat any
        # of them as "not a valid PDF" instead of letting it 500.
        raise InvalidPDFError("Could not read this file as a PDF.") from exc
    return text


def extract_skills(text: str) -> list[str]:
    """Extract skills from resume text using the same patterns as JD parser."""
    return extract_jd_skills(text)
