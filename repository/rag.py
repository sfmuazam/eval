from __future__ import annotations
import os
from typing import Optional, Sequence, List

from sqlalchemy import select, case
from sqlalchemy.orm import Session

from models import RagDoc
from models.Enums import RagDocType
from repository.embeddings import embed_one

# Pilih operator jarak: "l2" (default) atau "cosine"
_EMBED_OPS = (os.getenv("EMBED_OPS") or "l2").lower()  # "l2" | "cosine"


# ---------- Insert / upsert ----------
def add_doc(
    db: Session,
    *,
    doc_type: RagDocType,
    title: str,
    body: str,
    tags: Optional[list[str]] = None,
) -> RagDoc:
    vec = embed_one(f"{title}\n\n{body}")
    row = RagDoc(type=doc_type, title=title, body=body, tags=tags or [], embedding=vec)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def add_many(db: Session, docs: Sequence[tuple[RagDocType, str, str, list[str] | None]]) -> int:
    count = 0
    for t, title, body, tags in docs:
        add_doc(db, doc_type=t, title=title, body=body, tags=tags)
        count += 1
    return count

# ---------- Search (prioritize `current` + recency tie-breaker) ----------
def search(
    db: Session,
    *,
    query_text: str,
    top_k: int = 5,
    doc_type: Optional[RagDocType] = None,
    tags: Optional[list[str]] = None,
) -> list[tuple[str, str, float]]:
    """
    Return list of (title, body, score). Score ~[0..1].
    - Prioritizes docs that have tag 'current'
    - Tie-breaks by recency (updated_at DESC if available, else id DESC)
    If embed fails, fallback to non-vector ranking using the same priority/recency rules.
    """
    # kolom recency (updated_at kalau ada; fallback id)
    try:
        recency_col = RagDoc.updated_at.desc()  # type: ignore[attr-defined]
    except Exception:
        recency_col = RagDoc.id.desc()

    # 'current' duluan
    priority = case((RagDoc.tags.contains(['current']), 0), else_=1)

    try:
        qvec = embed_one(query_text)

        # pilih operator jarak
        if _EMBED_OPS == "cosine":
            dist_expr = RagDoc.embedding.cosine_distance(qvec)
        else:
            dist_expr = RagDoc.embedding.l2_distance(qvec)

        stmt = (
            select(RagDoc.id, RagDoc.title, RagDoc.body, dist_expr.label("distance"))
            .order_by(priority, dist_expr, recency_col)
            .limit(top_k)
        )
        if doc_type:
            stmt = stmt.where(RagDoc.type == doc_type)
        if tags:
            stmt = stmt.where(RagDoc.tags.contains(tags))

        rows = db.execute(stmt).all()
        out = []
        for _id, title, body, dist in rows:
            d = float(dist or 0.0)
            # skala skor 0..1 (kasar)
            score = (max(0.0, 1.0 - d / 2.0) if _EMBED_OPS == "cosine" else 1.0 / (1.0 + d))
            out.append((title, body, score))
        return out

    except Exception:
        # Fallback TANPA embedding: tetap prioritaskan 'current' dan recency
        stmt = select(RagDoc.id, RagDoc.title, RagDoc.body)
        if doc_type:
            stmt = stmt.where(RagDoc.type == doc_type)
        if tags:
            # gunakan overlap agar toleran (selama ada salah satu tag match)
            stmt = stmt.where(RagDoc.tags.overlap(tags))
        stmt = stmt.order_by(priority, recency_col).limit(top_k)

        rows = db.execute(stmt).all()
        # skor dummy 0.5 (karena tanpa jarak vektor)
        return [(title, body, 0.5) for _id, title, body in rows]


# ---------- Build contexts (dinamis, tanpa input dari API) ----------
def _dedup(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for x in seq or []:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out

def build_cv_context(
    db: Session,
    *,
    role_tag: Optional[str] = None,
    extra_query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    job_desc_text: Optional[str] = None,
    top_k: int = 4
) -> str:
    parts: list[str] = []

    # 0) inline JD (kalau suatu saat dibutuhkan)
    if job_desc_text:
        parts.append(job_desc_text.strip())

    # 1) CV rubric
    rubric_tags = _dedup((tags or []) + ["cv"] + ([role_tag] if role_tag else []))
    rubric = search(
        db,
        query_text=extra_query or (role_tag or "cv scoring rubric"),
        doc_type=RagDocType.rubric,
        tags=rubric_tags,
        top_k=min(2, max(1, top_k - (1 if job_desc_text else 0))),
    )

    # 2) Job description (ambil umum dari vector DB)
    if not job_desc_text and top_k > len(rubric):
        jd = search(
            db,
            query_text=role_tag or "job description",
            doc_type=RagDocType.job_desc,
            tags=_dedup((tags or []) + ([role_tag] if role_tag else [])),
            top_k=top_k - len(rubric),
        )
    else:
        jd = []

    for _, body, _ in rubric + jd:
        if body:
            parts.append(body.strip())

    return "\n\n---\n\n".join(parts)

def build_project_context(
    db: Session,
    *,
    role_tag: Optional[str] = None,
    extra_query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    job_desc_text: Optional[str] = None,
    top_k: int = 4
) -> str:
    parts: list[str] = []

    if job_desc_text:
        parts.append(job_desc_text.strip())

    rubric_tags = _dedup((tags or []) + ["project"] + ([role_tag] if role_tag else []))
    rubric = search(
        db,
        query_text=extra_query or (role_tag or "project scoring rubric"),
        doc_type=RagDocType.rubric,
        tags=rubric_tags,
        top_k=min(2, max(1, top_k - (1 if job_desc_text else 0))),
    )

    if not job_desc_text and top_k > len(rubric):
        jd = search(
            db,
            query_text=role_tag or "job description",
            doc_type=RagDocType.job_desc,
            tags=_dedup((tags or []) + ([role_tag] if role_tag else [])),
            top_k=top_k - len(rubric),
        )
    else:
        jd = []

    for _, body, _ in rubric + jd:
        if body:
            parts.append(body.strip())

    return "\n\n---\n\n".join(parts)

# ---------- Infer job title dari vector DB ----------
def infer_job_title(
    db: Session,
    *,
    role_tag: Optional[str] = None,
    tags: Optional[List[str]] = None,
    job_desc_text: Optional[str] = None,
    default: str = "General Role",
) -> str:
    # 1) kalau dikirim teks JD, ambil judul dari line pertama
    if job_desc_text and job_desc_text.strip():
        first_line = job_desc_text.strip().splitlines()[0].strip()
        if 3 <= len(first_line) <= 120:
            return first_line

    # 2) coba ambil dari vector DB: job_desc paling relevan
    rows = search(
        db,
        query_text=role_tag or "job description",
        doc_type=RagDocType.job_desc,
        tags=_dedup((tags or []) + ([role_tag] if role_tag else [])),
        top_k=1,
    )
    if rows:
        title, _body, _score = rows[0]
        if title and len(title.strip()) > 0:
            return title.strip()

    return default
