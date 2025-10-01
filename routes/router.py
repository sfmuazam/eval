from __future__ import annotations
import os
import uuid
from pathlib import Path
from typing import Optional, Generator, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from models.Enums import RagDocType
from pydantic import BaseModel
from repository.extract_text import extract_text_from_file
from repository.pipeline import run_pipeline_background
from repository.rag import add_doc
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import Upload, Job, Result, SessionLocal, RagDoc  

router = APIRouter(tags=["api"])

# ---- DB dependency (sinkron) ----
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- Folder uploads (robust) ----
PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", PROJECT_ROOT / "uploads")).resolve()
RAG_DIR = UPLOAD_DIR / "rag"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RAG_DIR.mkdir(parents=True, exist_ok=True)

# ---- Healthcheck ----
@router.get("/health")
def health() -> dict:
    return {"status": "ok"}

# ---- Upload rubric/JD ke vector DB (buat bisa tandai 'current') ----
@router.post("/rag/upload")
async def rag_upload(
    doc_type: RagDocType = Form(...),                  # 'rubric' | 'job_desc'
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),                  # comma-separated, e.g. "backend,cv"
    make_current: bool = Form(True),
    db: Session = Depends(get_db),
):
    # simpan file sementara lalu extract text
    ext = Path(file.filename).suffix.lower()
    tmp_name = f"rag_{uuid.uuid4()}{ext}"
    tmp_path = (RAG_DIR / tmp_name).resolve()
    with tmp_path.open("wb") as f:
        f.write(await file.read())

    text = extract_text_from_file(str(tmp_path))
    tag_list = [t.strip() for t in (tags.split(",") if tags else []) if t.strip()]

    # simpan dokumen baru
    row = add_doc(
        db,
        doc_type=doc_type,
        title=(title or Path(file.filename).stem),
        body=text,
        tags=tag_list or None,
    )

    if make_current:
        # 1) cabut tag 'current' dari dokumen lain dengan tipe sama (+ overlap tag jika ada)
        q = db.query(RagDoc).filter(RagDoc.type == doc_type)
        if tag_list:
            q = q.filter(RagDoc.tags.overlap(tag_list))
        for doc in q.all():
            if doc.id != row.id:
                doc.tags = [t for t in (doc.tags or []) if t != 'current']
        db.commit()

        # 2) tambahkan tag 'current' ke dokumen baru
        row.tags = list({*(row.tags or []), 'current'})
        db.add(row)
        db.commit()
        db.refresh(row)

    return {
        "id": str(row.id),
        "type": row.type.value if hasattr(row.type, "value") else str(row.type),
        "title": row.title,
        "tags": row.tags,
        "stored": True,
        "current": make_current,
    }

# ---- Upload CV & Project Report ----
@router.post("/upload")
async def upload_files(
    cv: UploadFile = File(...),
    project_report: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    allowed = {".pdf", ".docx", ".txt"}
    cv_ext = Path(cv.filename).suffix.lower()
    pr_ext = Path(project_report.filename).suffix.lower()
    if cv_ext not in allowed or pr_ext not in allowed:
        raise HTTPException(status_code=400, detail="Extension must be PDF/DOCX/TXT")

    cv_name = f"cv_{uuid.uuid4()}{cv_ext}"
    pr_name = f"report_{uuid.uuid4()}{pr_ext}"
    cv_path = UPLOAD_DIR / cv_name
    pr_path = UPLOAD_DIR / pr_name

    with cv_path.open("wb") as f:
        f.write(await cv.read())
    with pr_path.open("wb") as f:
        f.write(await project_report.read())

    cv_text = extract_text_from_file(str(cv_path))
    pr_text = extract_text_from_file(str(pr_path))

    up = Upload(cv_path=str(cv_path), report_path=str(pr_path), cv_text=cv_text, project_text=pr_text)
    db.add(up)
    db.commit()
    db.refresh(up)

    return {"upload_id": str(up.id), "cv_path": cv_name, "report_path": pr_name}

# ---- Evaluate & Result ----
class EvaluateRequest(BaseModel):
    upload_id: uuid.UUID

@router.post("/evaluate")
def evaluate(
    body: EvaluateRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    upload = db.get(Upload, body.upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="upload not found")

    job = Job(upload_id=upload.id)  # default status=queued
    db.add(job)
    db.commit()
    db.refresh(job)

    # Tanpa parameter role: pipeline akan membaca konteks dari vector DB
    background.add_task(run_pipeline_background, job.id)
    return {"id": str(job.id), "status": job.status.value}

@router.get("/result/{job_id}")
def result(job_id: uuid.UUID, debug: bool = False, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    res = db.scalar(select(Result).where(Result.job_id == job.id))
    base = {"id": str(job.id), "status": job.status.value, "error": job.error}

    if job.status.value != "completed":
        if debug and res:
            base["detail_scores"] = res.detail_scores
        return base

    payload = {
        **base,
        "result": {
            "cv_match_rate": res.cv_match_rate,
            "cv_feedback": res.cv_feedback,
            "project_score": res.project_score,
            "project_feedback": res.project_feedback,
            "overall_summary": res.overall_summary,
        },
    }
    if debug and res:
        payload["detail_scores"] = res.detail_scores
    return payload
