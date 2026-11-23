
import re
from typing import Optional, List, Any

from pydantic import BaseModel, Field


# -----------------------------------------
# 1. INPUT SCHEMA
# -----------------------------------------

class LogAnalysisInput(BaseModel):
    title: str = ""
    description: str = ""
    stack_trace: str = ""
    error_logs: str = ""


# -----------------------------------------
# 2. OUTPUT SCHEMA
# -----------------------------------------

class LogAnalysisOutput(BaseModel):
    exception_type: Optional[str] = None
    error_message: Optional[str] = None

    failure_file: Optional[str] = None
    failure_class: Optional[str] = None
    failure_method: Optional[str] = None
    line_number: Optional[int] = None

    probable_code_path: List[str] = Field(default_factory=list)

    confidence: float = Field(ge=0.0, le=1.0)

    reasoning: str
    evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)

    agent_version: str = "log-analysis-rules-v1"


# -----------------------------------------
# 3. EXCEPTION DETECTION
# -----------------------------------------

EXCEPTION_PATTERN = re.compile(
    r"\b((?:[A-Za-z_][A-Za-z0-9_.]*(?:Exception|Error|Fault))|Error)\b"
)


def detect_exception(text: str) -> Optional[str]:
    match = EXCEPTION_PATTERN.search(text or "")

    if match:
        return match.group(1).split(".")[-1]

    return None


# -----------------------------------------
# 4. ERROR MESSAGE EXTRACTION
# -----------------------------------------

def extract_error_message(text: str) -> Optional[str]:
    """
    Extracts an error message from common formats:
    - Java/Python/.NET exception lines
    - JavaScript TypeError and ReferenceError
    - ERROR/FATAL application log entries
    - Unhandled exception messages
    - Go panic messages
    """

    if not text:
        return None

    patterns = [
        # Java, Python, .NET and JavaScript exception messages
        r"^\s*(?:[\w.$]+\.)*[\w$]*(?:Exception|Error|Fault)\s*:\s*(.+?)\s*$",

        # Unhandled exception messages
        r"^\s*Unhandled exception\s*:\s*(.+?)\s*$",

        # Application logs such as:
        # ERROR LoginService - Authentication failed
        # ERROR: Database connection failed
        r"^\s*(?:ERROR|FATAL)\s+(?:[\w.$/-]+\s*)?[-:]\s*(.+?)\s*$",

        # Application logs such as ERROR: message
        r"^\s*(?:ERROR|FATAL)\s*:\s*(.+?)\s*$",

        # Go panic messages
        r"^\s*panic\s*:\s*(.+?)\s*$",

        # Caused by messages
        r"^\s*Caused by\s*:\s*(.+?)\s*$",
    ]

    lines = text.splitlines()

    # First look for explicit exception or panic messages.
    for line in lines:
        cleaned = line.strip()

        if not cleaned or cleaned.startswith("at "):
            continue

        for pattern in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)

            if match:
                message = match.group(1).strip()

                if message:
                    return message

    # Handle common JavaScript messages that may not have
    # an explicit exception prefix.
    fallback_patterns = [
        r"(Cannot read properties of [^\n]+)",
        r"(Cannot access '[^']+' before initialization)",
        r"(is not defined)",
        r"(is not a function)",
    ]

    for pattern in fallback_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1).strip()

    return None


# -----------------------------------------
# 5. STACK FRAME PARSING
# -----------------------------------------

def parse_stack_frames(text: str) -> List[dict]:
    frames = []

    patterns = [

        # Python:
        # File "app.py", line 25, in login
        (
            r'File "([^"]+)", line (\d+), in ([^\n]+)',
            "python"
        ),

        # Java:
        # at com.example.Login.authenticate(Login.java:42)
        (
            r'at ([\w.$<>]+)\(([^():]+):(\d+)\)',
            "java"
        ),

        # JavaScript / Node.js:
        # at Object.login (C:\project\app.js:10:5)
        (
            r'^\s*at\s+(.*?)\s+\((.+?):(\d+):(\d+)\)\s*$',
            "javascript_named"
        ),

        # JavaScript / Node.js:
        # at C:\project\app.js:10:5
        (
            r'^\s*at\s+(.+?):(\d+):(\d+)\s*$',
            "javascript_anonymous"
        ),

        # .NET:
        # at Namespace.Class.Method() in C:\app\File.cs:line 20
        (
            r'at ([\w.<>]+)\(.*?\) in (.+?):line (\d+)',
            "dotnet"
        ),

        # Go:
        # /project/main.go:23
        # main.go:23 +0x45
        (
            r'^\s*(.+?\.go):(\d+)(?:\s|$)',
            "go"
        ),
    ]

    for line in text.splitlines():
        line = line.strip()

        for pattern, language in patterns:
            match = re.search(pattern, line)

            if not match:
                continue

            groups = match.groups()

            if language == "python":
                frames.append({
                    "file": groups[0],
                    "line": int(groups[1]),
                    "method": groups[2].strip(),
                    "class": None,
                    "language": language
                })

            elif language == "java":
                method = groups[0]
                file = groups[1]

                class_name = (
                    method.rsplit(".", 1)[0]
                    if "." in method else None
                )

                frames.append({
                    "file": file,
                    "line": int(groups[2]),
                    "method": method,
                    "class": class_name,
                    "language": language
                })

            elif language == "javascript_named":
                frames.append({
                    "file": groups[1],
                    "line": int(groups[2]),
                    "method": groups[0].strip() or None,
                    "class": None,
                    "language": "javascript"
                })

            elif language == "javascript_anonymous":
                frames.append({
                    "file": groups[0],
                    "line": int(groups[1]),
                    "method": None,
                    "class": None,
                    "language": "javascript"
                })

            elif language == "dotnet":
                frames.append({
                    "file": groups[1],
                    "line": int(groups[2]),
                    "method": groups[0],
                    "class": (
                        groups[0].rsplit(".", 1)[0]
                        if "." in groups[0] else None
                    ),
                    "language": language
                })

            elif language == "go":
                frames.append({
                    "file": groups[0],
                    "line": int(groups[1]),
                    "method": None,
                    "class": None,
                    "language": language
                })

            break

    return frames


# -----------------------------------------
# 6. MAIN LOG ANALYSIS AGENT
# -----------------------------------------

def analyze_logs(bug: Any) -> LogAnalysisOutput:

    if isinstance(bug, dict):
        data = LogAnalysisInput(**bug)

    elif isinstance(bug, LogAnalysisInput):
        data = bug

    elif hasattr(bug, "model_dump"):
        data = LogAnalysisInput(**bug.model_dump())

    elif hasattr(bug, "dict"):
        data = LogAnalysisInput(**bug.dict())

    else:
        raise TypeError("Unsupported log analysis input")

    combined_text = "\n".join([
        data.title or "",
        data.description or "",
        data.stack_trace or "",
        data.error_logs or ""
    ])

    log_text = "\n".join([
        data.stack_trace or "",
        data.error_logs or "",
        data.description or ""
    ])

    evidence = []
    missing = []

    exception_type = detect_exception(combined_text)
    error_message = extract_error_message(log_text)

    frames = parse_stack_frames(
        (data.stack_trace or "") + "\n" + (data.error_logs or "")
    )

    failure_file = None
    failure_method = None
    failure_class = None
    line_number = None

    if frames:

        # The first parsed frame is a failure-location candidate,
        # not necessarily the confirmed root cause.
        primary = frames[0]

        failure_file = primary["file"]
        failure_method = primary["method"]
        failure_class = primary["class"]
        line_number = primary["line"]

        evidence.append(
            f"Stack frame detected: {failure_file}:{line_number}"
        )

    else:
        missing.append("Recognizable stack frame")

    if exception_type:
        evidence.append(
            f"Exception detected: {exception_type}"
        )
    else:
        missing.append("Exception type")

    if error_message:
        evidence.append(
            f"Error message detected: {error_message}"
        )
    else:
        missing.append("Error message")

    probable_code_path = [
        frame["file"]
        + (
            ":" + str(frame["line"])
            if frame["line"] else ""
        )
        + (
            " (" + frame["method"] + ")"
            if frame["method"] else ""
        )
        for frame in frames
    ]

    # -------------------------------------
    # 7. CONFIDENCE SCORING
    # -------------------------------------

    confidence = 0.20

    if exception_type:
        confidence += 0.20

    if error_message:
        confidence += 0.15

    if failure_file:
        confidence += 0.15

    if failure_method:
        confidence += 0.10

    if line_number:
        confidence += 0.10

    if len(frames) > 1:
        confidence += 0.10

    confidence = round(min(0.95, confidence), 2)

    # -------------------------------------
    # 8. REASONING
    # -------------------------------------

    if frames:
        reasoning = (
            f"Identified {len(frames)} stack frame(s). "
            f"The first parsed frame points to "
            f"{failure_file}, line {line_number}. "
            "This is a failure-location candidate, "
            "not a confirmed root cause."
        )
    else:
        reasoning = (
            "No recognizable stack frame was found. "
            "The available log text is insufficient "
            "to identify an exact failure location."
        )

    if exception_type:
        reasoning += (
            f" Detected exception type: {exception_type}."
        )

    if error_message:
        reasoning += (
            f" Error message: {error_message}."
        )

    return LogAnalysisOutput(
        exception_type=exception_type,
        error_message=error_message,
        failure_file=failure_file,
        failure_class=failure_class,
        failure_method=failure_method,
        line_number=line_number,
        probable_code_path=probable_code_path,
        confidence=confidence,
        reasoning=reasoning,
        evidence=evidence,
        missing_information=missing
    )


# -----------------------------------------
# 9. AGENT CLASS INTERFACE
# -----------------------------------------

class LogAnalysisAgent:

    def analyze(self, bug: Any) -> LogAnalysisOutput:
        return analyze_logs(bug)
