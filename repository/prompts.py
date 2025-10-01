from __future__ import annotations

# P1 — CV Extractor (struktur ketat)
P1_CV_EXTRACT = """You are an information extractor. Read the CV text and return a STRICT JSON object only.
Fields (all required):
- skills_backend: string[]  (e.g. ["python","fastapi","golang"])
- skills_db: string[]       (e.g. ["postgresql","mysql","redis"])
- skills_api: string[]      (e.g. ["rest","graphql","grpc"])
- skills_cloud: string[]    (e.g. ["aws","gcp","azure"])
- skills_ai: string[]       (e.g. ["rag","vector db","llm","ml"])
- experience_years: number  (total experience in years, can be decimal)
- projects: array of objects {{name: string, role: string, tech_stack: string[], impact: string}}

Return ONLY a valid JSON object. Do not include any extra text, explanations, or markdown.
CV:
---
{cv_text}
---
"""

# P2 — CV Scorer (role-agnostic)
P2_CV_SCORER = """You are a strict evaluator for the role: {job_title}.
Score the candidate's CV against the job description and the CV rubric.
Return ONLY a JSON with:
- skills: 1..5
- exp: 1..5
- ach: 1..5
- culture: 1..5
- feedback: string (1 paragraph)
Return ONLY a valid JSON object. Do not include any extra text, explanations, or markdown.

Guidelines:
- Use the extracted CV data (JSON) as the main source of truth.
- Use Job Description and CV Rubric as criteria.
- Clamp each score 1..5 (integer only).

INPUT:
[EXTRACTED_CV_JSON]
{cv_extracted}

[JOB_DESCRIPTION_AND_CV_RUBRIC_CONTEXT]
{cv_ctx}
"""

# P3 — Project Scorer (role-agnostic)
P3_PROJECT_SCORER = """You are a strict evaluator for the role: {job_title}.
Score the candidate's project report against the project rubric and job description.
Return ONLY a JSON with:
- corr: 1..5   (problem/requirement fit)
- code: 1..5   (code quality/structure)
- res:  1..5   (results/measurement)
- docs: 1..5   (docs/readability)
- bonus:1..5   (tests, reliability, retries, etc.)
- feedback: string (1 paragraph)
Return ONLY a valid JSON object. Do not include any extra text, explanations, or markdown.

Guidelines:
- Focus on the provided Project Text (not CV).
- Use Rubric + JD context.
- Clamp each score 1..5 (integer only).

INPUT:
[PROJECT_TEXT]
{project_text}

[PROJECT_RUBRIC_AND_JD_CONTEXT]
{project_ctx}
"""

# P4 — Overall Summarizer (role-agnostic)
P4_SUMMARIZER = """You are a hiring reviewer for the role: {job_title}.
Use the JSON scores and short contexts to craft a concise, evidence-based summary.

CV SCORES (JSON):
{cv_scores}

PROJECT SCORES (JSON):
{proj_scores}

EXCERPTS (may be empty):
- CV/JD context:
{cv_ctx}

- Project context:
{project_ctx}

Return JSON ONLY with this exact schema:
{{
  "overall_summary": "<max 3 sentences, concise but specific>",
  "recommendation": "strong_yes|yes|weak_yes|hold|no",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "next_steps": ["...", "..."]
}}
"""
