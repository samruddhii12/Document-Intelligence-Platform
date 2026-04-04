from pypdf import PdfReader
from docx import Document
from pathlib import Path
import re


def clean_text(text: str) -> str:
    """
    Basic cleanup for extracted document text.
    """
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_text(file_path: str) -> str:
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        text = extract_pdf(path)
    elif path.suffix.lower() == ".docx":
        text = extract_docx(path)
    else:
        raise ValueError("Unsupported file type")

    return clean_text(text)


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text)


def extract_docx(path: Path) -> str:
    doc = Document(str(path))
    text = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(text)