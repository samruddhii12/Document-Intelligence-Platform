import io
import zipfile
from pypdf import PdfReader
from docx import Document as DocxDocument
from markdown_it import MarkdownIt
from backend.config import settings

EXTRACTOR_VERSION="structured-v1"

def check_archive(content):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        total=sum(entry.file_size for entry in archive.infolist())
        if total>settings.MAX_UNPACKED_MB*1024*1024:
            raise ValueError("Decompressed document exceeds the size limit")
        if len(archive.infolist())>10000:
            raise ValueError("Too many archive entries")

def segment(content,page=None,section=None,**location):
    return {"content":content,"page_number":page,"section_title":section,"location":location}

def extract_segments(content:bytes,file_type:str):
    if file_type=="pdf":
        if not content.lstrip().startswith(b"%PDF-"): raise ValueError("Invalid PDF")
        reader=PdfReader(io.BytesIO(content))
        if reader.is_encrypted: raise ValueError("Encrypted PDF is not supported")
        if len(reader.pages)>1000: raise ValueError("PDF exceeds 1000 pages")
        return [segment(text,page=index,page_number=index) for index,page in enumerate(reader.pages,1)
                if (text:=(page.extract_text() or "").strip())]
    if file_type=="docx":
        check_archive(content)
        document=DocxDocument(io.BytesIO(content)); out=[]; headings={}
        # Preserve paragraph/table order in the underlying body.
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        for index,element in enumerate(document.element.body,1):
            if element.tag.endswith("}p"):
                paragraph=Paragraph(element,document); text=paragraph.text.strip()
                if not text: continue
                style=paragraph.style.name if paragraph.style else ""
                if style.startswith("Heading ") and style.split()[-1].isdigit():
                    level=int(style.split()[-1]); headings={k:v for k,v in headings.items() if k<level}; headings[level]=text
                out.append(segment(text,section=" / ".join(headings.values()) or None,paragraph=index))
            elif element.tag.endswith("}tbl"):
                table=Table(element,document)
                text="\n".join(" | ".join(cell.text for cell in row.cells) for row in table.rows)
                if text.strip(): out.append(segment(text,section=" / ".join(headings.values()) or None,table=index))
        return out
    if file_type not in {"md","txt"}: raise ValueError("Unsupported document format")
    text=content.decode("utf-8-sig")
    if "\x00" in text: raise ValueError("Binary content is not a text document")
    lines=text.splitlines(); out=[]; headings={}
    if file_type=="md":
        for token in MarkdownIt().parse(text):
            if token.type=="heading_open" and token.map:
                start,end=token.map; level=int(token.tag[1:])
                title=" ".join(lines[start:end]).strip("# ").strip()
                # Setext heading syntax has a separate underline.
                if end-start>1: title=lines[start].strip()
                headings={k:v for k,v in headings.items() if k<level}; headings[level]=title
            if token.map and token.type in {"heading_open","paragraph_open","fence","code_block","html_block"}:
                start,end=token.map
                body="\n".join(lines[start:end]).strip()
                if body: out.append(segment(body,section=" / ".join(headings.values()) or None,line_start=start+1,line_end=end))
    else:
        start=0
        for index in range(len(lines)+1):
            if index==len(lines) or not lines[index].strip():
                body="\n".join(lines[start:index]).strip()
                if body: out.append(segment(body,line_start=start+1,line_end=index))
                start=index+1
    return out
