from __future__ import annotations
from typing import List, Optional, Any
from pydantic import BaseModel, field_validator

class ProjectItem(BaseModel):
    name: str
    role: str = ""
    tech_stack: List[str] = []
    impact: str = ""

class CvExtractSchema(BaseModel):
    skills_backend: List[str] = []
    skills_db: List[str] = []
    skills_api: List[str] = []
    skills_cloud: List[str] = []
    skills_ai: List[str] = []
    experience_years: float = 0.0
    projects: List[ProjectItem] = []

    @field_validator("projects", mode="before")
    @classmethod
    def normalize_projects(cls, v: Any):
        # Terima berbagai bentuk: string, dict tanpa "name", dsb.
        if v is None:
            return []
        if not isinstance(v, list):
            v = [v]
        out = []
        for item in v:
            if isinstance(item, str):
                out.append({"name": item})
                continue
            if isinstance(item, dict):
                name = (
                    item.get("name")
                    or item.get("project_name")
                    or item.get("title")
                    or item.get("project")
                    or ""
                )
                role = item.get("role", "") or item.get("position", "")
                tech = item.get("tech_stack") or item.get("stack") or item.get("tech") or []
                if isinstance(tech, str):
                    # split kasar jika string dipisah koma
                    tech = [t.strip() for t in tech.split(",") if t.strip()]
                impact = item.get("impact", "") or item.get("result", "") or item.get("outcome", "")
                out.append({"name": name, "role": role, "tech_stack": tech, "impact": impact})
                continue
            # tipe lain: skip aman
        return out

class CvScoreSchema(BaseModel):
    skills: int
    exp: int
    ach: int
    culture: int
    feedback: str
    @field_validator("skills","exp","ach","culture", mode="before")
    @classmethod
    def clamp_1_5(cls, v):
        v = int(float(v))
        return max(1, min(5, v))

class ProjectScoreSchema(BaseModel):
    corr: int
    code: int
    res: int
    docs: int
    bonus: int
    feedback: str
    @field_validator("corr","code","res","docs","bonus", mode="before")
    @classmethod
    def clamp_1_5(cls, v):
        v = int(float(v))
        return max(1, min(5, v))
