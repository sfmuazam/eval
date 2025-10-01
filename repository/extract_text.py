from __future__ import annotations
import os
import mimetypes

from pdfminer.high_level import extract_text as pdf_extract_text
try:
    import docx  
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False

def _read_txt(path: str, limit_mb: float = 5.0) -> str:
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > limit_mb:
        raise ValueError(f"TXT too large: {size_mb:.2f} MB > {limit_mb} MB")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _read_pdf(path: str, limit_mb: float = 20.0) -> str:
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > limit_mb:
        raise ValueError(f"PDF too large: {size_mb:.2f} MB > {limit_mb} MB")
    return pdf_extract_text(path) or ""

def _read_docx(path: str, limit_mb: float = 20.0) -> str:
    if not HAS_DOCX:
        raise RuntimeError("python-docx not installed")
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > limit_mb:
        raise ValueError(f"DOCX too large: {size_mb:.2f} MB > {limit_mb} MB")
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs).strip()

def sniff_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().strip(".")
    if ext in {"txt"}: return "txt"
    if ext in {"pdf"}: return "pdf"
    if ext in {"docx"}: return "docx"
    mime, _ = mimetypes.guess_type(path)
    if mime == "application/pdf": return "pdf"
    if mime in {"text/plain", "text/markdown"}: return "txt"
    return "unknown"

def extract_text_from_file(path: str) -> str:
    kind = sniff_type(path)
    if kind == "txt":  return _read_txt(path)
    if kind == "pdf":  return _read_pdf(path)
    if kind == "docx": return _read_docx(path)
    try:
        return _read_txt(path, limit_mb=1.0)
    except Exception:
        return ""
