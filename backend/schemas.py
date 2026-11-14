from pydantic import BaseModel, Field
from typing import List

class AttachmentOut(BaseModel):
    original_name: str
    file_type: str
    file_size: int
    sha256: str

class BugReportOut(BaseModel):
    bug_id: str
    title: str
    project_name: str
    programming_language: str
    severity: str
    description: str
    stack_trace: str
    error_logs: str
    status: str
    created_at: str
    attachments: List[AttachmentOut] = Field(default_factory=list)

class SimilarBugOut(BaseModel):
    historical_bug_id: str
    summary: str
    description: str
    project: str
    component: str
    severity: str
    status: str
    issue_url: str
    matched_chunk_type: str
    similarity_score: float


class BugSubmissionResponse(BugReportOut):
    similar_bugs: List[SimilarBugOut] = Field(default_factory=list)
    retrieval_status: str = "completed"

