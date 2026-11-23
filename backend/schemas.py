from pydantic import BaseModel, Field
from typing import List
from typing import List, Optional, Dict, Any

class AttachmentOut(BaseModel):
    original_name: str
    file_type: str
    file_size: int
    sha256: str
class TriageResultOut(BaseModel):
    bug_category: str
    severity: str
    priority: str
    affected_component: str
    confidence: float
    reasoning: str
    evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    reported_severity: Optional[str] = None
    agent_version: str = "triage-rules-v1"

class LogAnalysisResultOut(BaseModel):
    exception_type: Optional[str] = None
    error_message: Optional[str] = None

    failure_file: Optional[str] = None
    failure_class: Optional[str] = None
    failure_method: Optional[str] = None
    line_number: Optional[int] = None

    probable_code_path: List[str] = Field(default_factory=list)

    confidence: float
    reasoning: str

    evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)

    agent_version: str = "log-analysis-rules-v1"


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
    triage: Optional[TriageResultOut] = None
    triage_status: str = "pending"
    triage_error: Optional[str] = None

    log_analysis: Optional[LogAnalysisResultOut] = None
    log_analysis_status: str = "pending"
    log_analysis_error: Optional[str] = None

    agent_context: Optional[Dict[str, Any]] = None
    orchestration_status: str = "pending"


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

