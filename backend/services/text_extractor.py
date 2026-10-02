from pathlib import Path
import re

from docx import Document
from pypdf import PdfReader


def clean_text(text: str) -> str:
    """
    Basic cleanup for extracted document text.
    """
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def extract_text(file_path: str) -> str:
    """
    Backward-compatible plain-text extraction.

    This keeps existing parts of the application working
    while Phase 2 introduces metadata-aware extraction.
    """
    segments = extract_document_segments(file_path)

    return "\n\n".join(
        segment["text"]
        for segment in segments
        if segment["text"].strip()
    )


def extract_document_segments(file_path: str) -> list[dict]:
    """
    Extract structured text segments from a document.

    PDF:
        one segment per page

    DOCX:
        one segment per meaningful paragraph

    Each segment carries metadata that can later
    be attached to chunks and citations.
    """
    path = Path(file_path)

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_segments(path)

    if suffix == ".docx":
        return extract_docx_segments(path)

    raise ValueError("Unsupported file type")


def extract_pdf_segments(path: Path) -> list[dict]:
    """
    Extract PDF text page by page.
    """
    reader = PdfReader(str(path))

    segments = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        page_text = page.extract_text() or ""
        page_text = clean_text(page_text)

        if not page_text:
            continue

        segments.append(
            {
                "page_number": page_number,
                "section_title": None,
                "text": page_text,
            }
        )

    return segments


def extract_docx_segments(path: Path) -> list[dict]:
    """
    Extract DOCX content paragraph by paragraph.

    DOCX files do not expose reliable fixed page numbers,
    so page_number remains None.
    """
    doc = Document(str(path))

    segments = []

    for paragraph in doc.paragraphs:
        text = clean_text(paragraph.text)

        if not text:
            continue

        style_name = (
            paragraph.style.name
            if paragraph.style is not None
            else ""
        )

        section_title = None

        if style_name.lower().startswith("heading"):
            section_title = text

        segments.append(
            {
                "page_number": None,
                "section_title": section_title,
                "text": text,
            }
        )

    return segments