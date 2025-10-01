from __future__ import annotations
import enum

class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class RagDocType(str, enum.Enum):
    job_desc = "job_desc"
    rubric = "rubric" 