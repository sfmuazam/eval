# repository/heuristics.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

# --- Kamus kata kunci sederhana ---
SKILLS = {
    "backend": {
        "python","fastapi","flask","django","golang","go","node","express","java","spring",
        "kotlin","c#",".net","rust","grpc","graphql","rest","celery","kafka","rabbitmq"
    },
    "db": {
        "postgres","postgresql","mysql","sqlite","mssql","redis","mongodb","clickhouse",
        "elasticsearch","neo4j","snowflake","bigquery","dwh","data warehouse","pgvector"
    },
    "api": {
        "rest","graphql","grpc","openapi","swagger","oauth","oidc","websocket"
    },
    "cloud": {
        "aws","gcp","azure","docker","kubernetes","k8s","terraform","ansible","helm","eks","gke","aks","lambda","cloud run"
    },
    "ai": {
        "llm","rag","vector","embeddings","ml","machine learning","openai","groq","ollama","qdrant","weaviate","milvus"
    }
}

ACHIEVEMENT_HINTS = {
    "improve","improved","increase","increased","reduce","reduced","optimize","optimized",
    "latency","throughput","qps","rps","availability","uptime","99.","slo","sla","cost","efficiency",
    "%","x","kpi","metric","conversion","retention","users","revenue"
}

CULTURE_HINTS = {
    "mentor","mentored","lead","led","leadership","collaborate","collaboration","pair programming",
    "ownership","communication","cross-functional","code review","open source","community"
}

PROJECT_BONUS = {
    "test","unit test","integration test","retry","backoff","circuit breaker","rate limit",
    "observability","metrics","monitoring","tracing","sentry","otel","chaos"
}

DOCS_HINTS = {"readme","docs","documentation","adr","architecture","diagram","design"}

CODE_QUALITY = {"modular","clean code","refactor","pattern","ddd","hexagonal","solid","typing","lint","mypy","pylint","flake8","black"}

def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9\+\.#]+", text.lower()) if t]

def _count_hits(text: str, vocab: set[str]) -> int:
    toks = _tokenize(text)
    return sum(1 for t in toks if t in vocab)

def _uniq(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out


# --- 1) Heuristic CV extractor ---
def extract_cv(cv_text: str) -> Dict[str, Any]:
    txt = (cv_text or "").strip()
    toks = _tokenize(txt)

    def find_skills(key: str) -> List[str]:
        vocab = SKILLS.get(key, set())
        hits = [t for t in toks if t in vocab]
        for phrase in list(SKILLS.get(key, set())):
            if " " in phrase and phrase in txt.lower():
                hits.append(phrase)
        return _uniq(hits)

    # experience_years: cari "X years|yr|tahun|thn"
    exp = 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|tahun|thn)", txt, re.I)
    if m:
        try:
            exp = float(m.group(1))
        except Exception:
            exp = 0.0

    # projects: ambil sampai 3 baris yang tampak seperti judul proyek
    projects: List[Dict[str, Any]] = []
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    for ln in lines:
        if len(projects) >= 3:
            break
        if re.match(r"^[-\*\•\d\)]\s+", ln) or "project" in ln.lower() or "proyek" in ln.lower() or "projek" in ln.lower():
            name = re.sub(r"^[-\*\•\d\)]\s+", "", ln).strip()
            if name and len(name) > 3:
                projects.append({
                    "name": name[:80],
                    "role": "",
                    "tech_stack": [],
                    "impact": "",
                })

    return {
        "skills_backend": find_skills("backend"),
        "skills_db":      find_skills("db"),
        "skills_api":     find_skills("api"),
        "skills_cloud":   find_skills("cloud"),
        "skills_ai":      find_skills("ai"),
        "experience_years": exp,
        "projects": projects,
    }


# --- 2) Heuristic CV scorer ---
def _bin_1_5(v: float, cuts: Tuple[float, float, float, float] = (1, 2, 4, 6)) -> int:
    if v < cuts[0]: return 1
    if v < cuts[1]: return 2
    if v < cuts[2]: return 3
    if v < cuts[3]: return 4
    return 5

def score_cv(cv_extracted: Dict[str, Any], cv_ctx: str = "") -> Dict[str, Any]:
    # skills score: gabungan kategori; semakin banyak match → semakin tinggi
    total_skills = sum(len(cv_extracted.get(k, [])) for k in
                       ["skills_backend","skills_db","skills_api","skills_cloud","skills_ai"])
    # bobot dikit kalau konteks JD menyebut kategori tertentu
    ctx_bonus = 0
    if any(key in (cv_ctx or "").lower() for key in ["backend","api","service","microservice"]):
        ctx_bonus += 1
    skills = min(5, max(1, total_skills // 4 + ctx_bonus))  

    # pengalaman
    exp = _bin_1_5(float(cv_extracted.get("experience_years") or 0))

    # achievements: hitung kata kunci capaian
    ach_hits = _count_hits(" ".join([
        " ".join(p.get("impact","") for p in cv_extracted.get("projects", [])),
        cv_ctx or ""
    ]), ACHIEVEMENT_HINTS)
    ach = min(5, max(1, 2 + ach_hits // 3))

    # culture: dari kata kunci kolaborasi/mentoring/ownership
    culture_hits = _count_hits(cv_ctx, CULTURE_HINTS)
    culture = min(5, max(1, 2 + culture_hits // 2))

    feedback = (
        f"Matched ~{total_skills} skills; experience bin={exp}/5; "
        f"achievement hints={ach_hits}; culture hints={culture_hits}."
    )
    return {"skills": skills, "exp": exp, "ach": ach, "culture": culture, "feedback": feedback}


# --- 3) Heuristic Project scorer ---
def score_project(project_text: str, project_ctx: str = "") -> Dict[str, Any]:
    txt = (project_text or "")
    ctx = (project_ctx or "")
    # corr: kedekatan sederhana terhadap kata kunci role/jd
    corr_hits = _count_hits(txt + " " + ctx, {"backend","api","service","postgres","scalab", "scalable","reliable","performance"})
    corr = min(5, max(1, 2 + corr_hits // 3))

    # code: indikator kualitas
    code_hits = _count_hits(txt, CODE_QUALITY)
    code = min(5, max(1, 2 + code_hits // 2))

    # res: ada angka/%, latency, throughput, dsb
    res_hits = len(re.findall(r"\b\d+(\.\d+)?\s*(%|ms|s|qps|rps|req/s|x)\b", txt.lower())) + _count_hits(txt, {"latency","throughput","p95","p99"})
    res = min(5, max(1, 2 + res_hits // 2))

    # docs: indikasi dokumentasi
    docs_hits = _count_hits(txt, DOCS_HINTS)
    docs = min(5, max(1, 2 + (docs_hits // 2)))

    # bonus: reliability/tooling ekstra
    bonus_hits = _count_hits(txt, PROJECT_BONUS)
    bonus = min(5, max(1, 1 + bonus_hits // 2))

    feedback = (
        f"corr={corr_hits} hits, code={code_hits}, results={res_hits}, "
        f"docs={docs_hits}, bonus={bonus_hits}."
    )
    return {"corr": corr, "code": code, "res": res, "docs": docs, "bonus": bonus, "feedback": feedback}


# --- 4) Heuristic summarizer ---
def summarize(cv_scores: Dict[str, Any], proj_scores: Dict[str, Any]) -> str:
    cm = (cv_scores.get("skills",3) + cv_scores.get("exp",3) + cv_scores.get("ach",3) + cv_scores.get("culture",3)) / 4
    pj = (proj_scores.get("corr",3) + proj_scores.get("code",3) + proj_scores.get("res",3) +
          proj_scores.get("docs",3) + proj_scores.get("bonus",3)) / 5
    return (
        f"CV average {cm:.1f}/5 dan skor proyek {pj:.1f}/5. "
        f"{(cv_scores.get('feedback') or '').strip()} {(proj_scores.get('feedback') or '').strip()}"
    ).strip()
