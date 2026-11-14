import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app_database import get_connection
from schemas import BugReportOut, BugSubmissionResponse
from retrieval import find_similar_bugs
router = APIRouter(tags=["Bug Reports"])
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".log", ".json", ".csv", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_FILES = 5
SEVERITIES = {"Low", "Medium", "High", "Critical"}

def validate_file_content(filename: str, content: bytes):
    ext = Path(filename).suffix.lower()
    if ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(400, detail=f"{filename}: file does not appear to be a valid PDF.")
    if ext == ".json":
        try:
            json.loads(content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(400, detail=f"{filename}: invalid JSON file.")
    if ext in {".txt", ".log", ".csv"}:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(400, detail=f"{filename}: file must be UTF-8 text.")

def serialize_bug(conn, row):
    attachments = conn.execute(
        "SELECT original_name, file_type, file_size, sha256 FROM attachments WHERE bug_id=?",
        (row["bug_id"],)
    ).fetchall()
    return {
        **dict(row),
        "attachments": [dict(a) for a in attachments]
    }


@router.post("/bugs", response_model=BugSubmissionResponse, status_code=201)
async def create_bug(
    title: str = Form(...),
    project_name: str = Form(""),
    programming_language: str = Form(""),
    severity: str = Form(...),
    description: str = Form(...),
    stack_trace: str = Form(""),
    error_logs: str = Form(""),
    files: Optional[List[UploadFile]] = File(None),
):
    # 1. Validate text fields
    title = title.strip()
    description = description.strip()
    project_name = project_name.strip()
    programming_language = programming_language.strip()

    if not title:
        raise HTTPException(422, detail="Bug title is required.")

    if len(title) > 180:
        raise HTTPException(422, detail="Bug title must be 180 characters or fewer.")

    if not description:
        raise HTTPException(422, detail="Bug description is required.")

    if len(description) > 20000:
        raise HTTPException(422, detail="Bug description must be 20,000 characters or fewer.")

    if severity not in SEVERITIES:
        raise HTTPException(
            422,
            detail="Severity must be Low, Medium, High, or Critical."
        )

    if len(stack_trace) > 100000 or len(error_logs) > 100000:
        raise HTTPException(
            422,
            detail="Stack trace and error logs must each be 100,000 characters or fewer."
        )

    # 2. Validate uploaded files
    files = files or []

    if len(files) > MAX_FILES:
        raise HTTPException(
            400,
            detail=f"You can upload at most {MAX_FILES} files."
        )

    prepared = []
    total_bytes = 0

    for upload in files:
        if not upload.filename:
            continue

        original_name = Path(
            upload.filename.replace("\\", "/")
        ).name

        ext = Path(original_name).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                400,
                detail=f"Unsupported file type: {ext or 'no extension'}. "
                       "Allowed: TXT, LOG, JSON, CSV, PDF."
            )

        content = await upload.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                413,
                detail=f"{original_name} exceeds the 10 MB per-file limit."
            )

        total_bytes += len(content)

        if total_bytes > 25 * 1024 * 1024:
            raise HTTPException(
                413,
                detail="Combined upload size cannot exceed 25 MB."
            )

        validate_file_content(original_name, content)

        digest = hashlib.sha256(content).hexdigest()
        stored_name = f"{uuid.uuid4().hex}{ext}"

        prepared.append((
            original_name,
            stored_name,
            ext[1:],
            len(content),
            digest,
            content
        ))

    # 3. Generate bug ID and timestamp
    bug_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    saved_paths = []

    try:
        # 4. Save uploaded files
        for item in prepared:
            path = UPLOAD_DIR / item[1]
            path.write_bytes(item[5])
            saved_paths.append(path)

        # 5. Store bug report and attachment details
        with get_connection() as conn:

            conn.execute("""
                INSERT INTO bug_reports
                (
                    bug_id,
                    title,
                    project_name,
                    programming_language,
                    severity,
                    description,
                    stack_trace,
                    error_logs,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bug_id,
                title,
                project_name,
                programming_language,
                severity,
                description,
                stack_trace,
                error_logs,
                "Submitted",
                created_at
            ))

            for item in prepared:
                conn.execute("""
                    INSERT INTO attachments
                    (
                        bug_id,
                        original_name,
                        stored_name,
                        file_type,
                        file_size,
                        sha256
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    bug_id,
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4]
                ))

            row = conn.execute(
                "SELECT * FROM bug_reports WHERE bug_id = ?",
                (bug_id,)
            ).fetchone()

            bug_data = serialize_bug(conn, row)

        # 6. Prepare query for historical bug retrieval
        query = "\n".join([
            title,
            project_name,
            programming_language,
            description,
            stack_trace,
            error_logs
        ])

        # 7. Find similar historical bugs using FAISS
        try:
            similar_bugs = find_similar_bugs(
                query,
                top_k=5
            )

            retrieval_status = "completed"

        except Exception as retrieval_error:
            print(
                "Historical bug retrieval error:",
                retrieval_error
            )

            similar_bugs = []
            retrieval_status = "unavailable"

        # 8. Add retrieval results to response
        bug_data["similar_bugs"] = similar_bugs
        bug_data["retrieval_status"] = retrieval_status

        return bug_data

    except Exception:
        # 9. Remove saved files if submission fails
        for path in saved_paths:
            path.unlink(missing_ok=True)

        raise


@router.get("/bugs", response_model=List[BugReportOut])
def list_bugs(limit: int = 50):
    limit = max(1, min(limit, 100))
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM bug_reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [serialize_bug(conn, row) for row in rows]

@router.get("/bugs/{bug_id}", response_model=BugReportOut)
def get_bug(bug_id: str):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM bug_reports WHERE bug_id=?", (bug_id,)).fetchone()
        if not row:
            raise HTTPException(404, detail="Bug report not found.")
        return serialize_bug(conn, row)
