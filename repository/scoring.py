from __future__ import annotations

def aggregate_cv(scores: dict) -> float:
    # 1..5
    s = 0.40 * scores.get("skills", 3) + 0.25 * scores.get("exp", 3) + 0.20 * scores.get("ach", 3) + 0.15 * scores.get("culture", 3)
    return max(1.0, min(5.0, s))

def aggregate_project(scores: dict) -> float:
    # 1..5
    s = (0.30 * scores.get("corr", 3) + 0.25 * scores.get("code", 3) +
         0.20 * scores.get("res", 3) + 0.15 * scores.get("docs", 3) +
         0.10 * scores.get("bonus", 3))
    return max(1.0, min(5.0, s))
