from pathlib import Path
from pypdf import PdfReader
from docx import Document as DocxDocument

def extract_segments(path: str):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        out=[]
        for i,page in enumerate(reader.pages,1):
            text=(page.extract_text() or "").strip()
            if text: out.append({"page_number":i,"section_title":None,"content":text})
        return out
    if p.suffix.lower() == ".docx":
        doc=DocxDocument(path)
        out=[]; section=None
        for para in doc.paragraphs:
            text=para.text.strip()
            if not text: continue
            if para.style and para.style.name.startswith("Heading"): section=text
            out.append({"page_number":None,"section_title":section,"content":text})
        return out
    raise ValueError("Unsupported file type")
