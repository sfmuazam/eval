from __future__ import annotations
import os, uuid, json, traceback
from typing import Any, List, Dict

from settings import USE_LLM
from sqlalchemy.orm import Session

from models.Enums import JobStatus
from models import Job, Result, Upload, SessionLocal
from repository.scoring import aggregate_cv, aggregate_project
from repository.rag import build_cv_context, build_project_context, infer_job_title
from core.utils import safe_format  # tetap ada untuk mode LLM

# Heuristic (NO LLM) tools
from repository.heuristics import extract_cv as hx_extract_cv
from repository.heuristics import score_cv as hx_score_cv
from repository.heuristics import score_project as hx_score_project
from repository.heuristics import summarize as hx_summarize

# LLM tools (optional)
use_llm = USE_LLM

if use_llm:
    from repository.llm_client import get_llm
    from repository.prompts import P1_CV_EXTRACT, P2_CV_SCORER, P3_PROJECT_SCORER, P4_SUMMARIZER


# ============================== Normalizers (shared) ==============================

def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        return [s.strip() for s in x.split(",") if s.strip()]
    return [x]

def coerce_projects(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        items = []
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]

    out: List[Dict[str, Any]] = []
    for idx, it in enumerate(items):
        name = f"project-{idx+1}"
        role = ""
        tech: List[str] = []
        impact = ""
        try:
            if isinstance(it, str):
                cand = it.strip()
                if cand:
                    name = cand
            elif isinstance(it, dict):
                cand_name = (
                    it.get("name") or it.get("project_name") or
                    it.get("title") or it.get("project") or ""
                )
                cand_name = str(cand_name).strip() if cand_name is not None else ""
                if cand_name:
                    name = cand_name

                cand_role = it.get("role") or it.get("position") or ""
                role = str(cand_role) if cand_role is not None else ""

                cand_tech = it.get("tech_stack") or it.get("stack") or it.get("tech") or []
                if isinstance(cand_tech, str):
                    tech = [t.strip() for t in cand_tech.split(",") if t.strip()]
                elif isinstance(cand_tech, list):
                    tech = [str(t).strip() for t in cand_tech if str(t).strip()]
                else:
                    tech = [str(cand_tech)] if cand_tech not in (None, "") else []

                cand_impact = it.get("impact") or it.get("result") or it.get("outcome") or ""
                impact = str(cand_impact) if cand_impact is not None else ""
        except Exception:
            pass

        if not name:
            name = f"project-{idx+1}"
        out.append({"name": name, "role": role, "tech_stack": tech, "impact": impact})
    return out

def coerce_cv_extracted(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    try:
        exp_years = float(raw.get("experience_years") or 0)
    except Exception:
        exp_years = 0.0
    return {
        "skills_backend": _as_list(raw.get("skills_backend")),
        "skills_db":      _as_list(raw.get("skills_db")),
        "skills_api":     _as_list(raw.get("skills_api")),
        "skills_cloud":   _as_list(raw.get("skills_cloud")),
        "skills_ai":      _as_list(raw.get("skills_ai")),
        "experience_years": exp_years,
        "projects": coerce_projects(raw.get("projects")),
    }

def _clamp_1_5(v: Any) -> int:
    try:
        return max(1, min(5, int(float(v))))
    except Exception:
        return 3

def coerce_cv_scores(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    return {
        "skills":  _clamp_1_5(raw.get("skills")),
        "exp":     _clamp_1_5(raw.get("exp")),
        "ach":     _clamp_1_5(raw.get("ach")),
        "culture": _clamp_1_5(raw.get("culture")),
        "feedback": str(raw.get("feedback") or ""),
    }

def coerce_project_scores(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    return {
        "corr": _clamp_1_5(raw.get("corr")),
        "code": _clamp_1_5(raw.get("code")),
        "res":  _clamp_1_5(raw.get("res")),
        "docs": _clamp_1_5(raw.get("docs")),
        "bonus": _clamp_1_5(raw.get("bonus")),
        "feedback": str(raw.get("feedback") or ""),
    }


# ============================== Pipeline ==============================

def run_pipeline_background(job_id: uuid.UUID) -> None:
    db: Session = SessionLocal()
    step = "init"
    try:
        job = db.get(Job, job_id)
        if not job:
            return

        # mark processing
        job.status = JobStatus.processing
        db.add(job); db.commit(); db.refresh(job)

        # sumber teks
        upload: Upload = db.get(Upload, job.upload_id)
        cv_text = (upload.cv_text or "").strip() if upload else ""
        project_text = (upload.project_text or "").strip() if upload else ""

        # --- RAG contexts & inferred job title ---
        step = "rag_contexts"
        cv_ctx = ""
        project_ctx = ""
        job_title = "General Role"
        warnings: list[str] = []
        try:
            cv_ctx = build_cv_context(db)
        except Exception as e:
            warnings.append(f"build_cv_context: {e}")
        try:
            project_ctx = build_project_context(db)
        except Exception as e:
            warnings.append(f"build_project_context: {e}")
        try:
            job_title = infer_job_title(db, default="General Role")
        except Exception as e:
            warnings.append(f"infer_job_title: {e}")

        if USE_LLM:
            # ================= LLM MODE =================
            llm = get_llm()
            llm_raw = {"p1": None, "p2": None, "p3": None, "p4": None}

            # P1 Extract
            step = "p1_extract"
            p1 = safe_format(P1_CV_EXTRACT, cv_text=cv_text[:20000])
            p1_json = llm.generate_json(p1, temperature=0.0, max_tokens=512)
            llm_raw["p1"] = getattr(llm, "last_raw", None)
            try:
                cv_extracted = coerce_cv_extracted(p1_json)
            except Exception as e:
                warnings.append(f"P1 coerce error: {e}")
                cv_extracted = coerce_cv_extracted({})

            # P2 CV Score
            step = "p2_cv_score"
            p2 = safe_format(
                P2_CV_SCORER,
                job_title=job_title,
                cv_extracted=json.dumps(cv_extracted, ensure_ascii=False),
                cv_ctx=cv_ctx[:20000],
            )
            p2_json = llm.generate_json(p2, temperature=0.1, max_tokens=256)
            llm_raw["p2"] = getattr(llm, "last_raw", None)
            try:
                cv_scores = coerce_cv_scores(p2_json)
            except Exception as e:
                warnings.append(f"P2 coerce error: {e}")
                cv_scores = {"skills": 3, "exp": 3, "ach": 3, "culture": 3, "feedback": "fallback"}

            # P3 Project Score
            step = "p3_project_score"
            p3 = safe_format(
                P3_PROJECT_SCORER,
                job_title=job_title,
                project_text=project_text[:20000],
                project_ctx=project_ctx[:20000],
            )
            p3_json = llm.generate_json(p3, temperature=0.1, max_tokens=256)
            llm_raw["p3"] = getattr(llm, "last_raw", None)
            try:
                proj_scores = coerce_project_scores(p3_json)
            except Exception as e:
                warnings.append(f"P3 coerce error: {e}")
                proj_scores = {"corr": 3, "code": 3, "res": 3, "docs": 3, "bonus": 3, "feedback": "fallback"}

            # Aggregate numbers
            step = "aggregate"
            cv_match   = aggregate_cv(cv_scores) * 20.0  # → 0..100
            proj_score = aggregate_project(proj_scores)   # → 1..5

            # P4 Summary
            step = "p4_summary"
            p4 = safe_format(
                P4_SUMMARIZER,
                job_title=job_title,
                cv_scores=json.dumps(cv_scores, ensure_ascii=False),
                proj_scores=json.dumps(proj_scores, ensure_ascii=False),
                cv_ctx=cv_ctx[:4000],
                project_ctx=project_ctx[:4000],
            )
            summary_json = {}
            try:
                summary_json = llm.generate_json(p4, temperature=0.2, max_tokens=256)
            except Exception as e:
                warnings.append(f"P4 generate_json error: {e}")
                summary_json = {}
            llm_raw["p4"] = getattr(llm, "last_raw", None)

            overall_text = (summary_json.get("overall_summary") or "").strip() if isinstance(summary_json, dict) else ""
            if not overall_text:
                overall_text = (
                    f"CV match {cv_match:.0f}% dan skor proyek {proj_score:.1f}/5. "
                    f"{cv_scores.get('feedback','').strip()} {proj_scores.get('feedback','').strip()}"
                ).strip()

            # Save
            step = "save_result"
            res = Result(
                job_id=job.id,
                cv_match_rate=cv_match,
                project_score=proj_score,
                cv_feedback=cv_scores.get("feedback", ""),
                project_feedback=proj_scores.get("feedback", ""),
                overall_summary=overall_text,
                detail_scores={
                    "mode": "llm",
                    "cv": cv_scores,
                    "project": proj_scores,
                    "cv_extract": cv_extracted,
                    "summary": summary_json,
                    "llm_raw": llm_raw,
                    "warnings": warnings,
                    "job_title": job_title,
                },
            )
            db.add(res)
            job.status = JobStatus.completed
            db.commit()
        else:
            # ================= NO-LLM (Heuristic) MODE =================
            step = "hx_extract"
            cv_extracted = hx_extract_cv(cv_text)

            step = "hx_cv_score"
            cv_scores = hx_score_cv(cv_extracted, cv_ctx=cv_ctx)

            step = "hx_proj_score"
            proj_scores = hx_score_project(project_text, project_ctx=project_ctx)

            step = "aggregate"
            cv_match   = aggregate_cv(cv_scores) * 20.0
            proj_score = aggregate_project(proj_scores)

            step = "hx_summary"
            overall_text = hx_summarize(cv_scores, proj_scores)

            step = "save_result"
            res = Result(
                job_id=job.id,
                cv_match_rate=cv_match,
                project_score=proj_score,
                cv_feedback=cv_scores.get("feedback", ""),
                project_feedback=proj_scores.get("feedback", ""),
                overall_summary=overall_text,
                detail_scores={
                    "mode": "heuristic",
                    "cv": cv_scores,
                    "project": proj_scores,
                    "cv_extract": cv_extracted,
                    "warnings": warnings,
                    "job_title": job_title,
                },
            )
            db.add(res)
            job.status = JobStatus.completed
            db.commit()

    except Exception as e:
        db.rollback()
        try:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error = json.dumps({
                    "type": e.__class__.__name__,
                    "message": str(e),
                    "step": step,
                    "traceback": traceback.format_exc(limit=4),
                }, ensure_ascii=False)
                db.add(job)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
