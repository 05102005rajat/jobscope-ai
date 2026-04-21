from PyPDF2 import PdfReader
from app.utils.jd_parser import extract_jd_skills
import io


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(io.BytesIO(content))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_skills(text: str) -> list[str]:
    """Extract skills from resume text using the same patterns as JD parser."""
    return extract_jd_skills(text)
