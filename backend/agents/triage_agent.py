
import re
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# -----------------------------------------
# 1. INPUT SCHEMA
# -----------------------------------------

class TriageInput(BaseModel):
    title: str = ""
    description: str = ""
    project_name: Optional[str] = None
    programming_language: Optional[str] = None
    severity: Optional[str] = None


# -----------------------------------------
# 2. OUTPUT SCHEMA
# -----------------------------------------

class TriageOutput(BaseModel):
    bug_category: str
    severity: str
    priority: str
    affected_component: str

    confidence: float = Field(ge=0.0, le=1.0)

    reasoning: str
    evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)

    reported_severity: Optional[str] = None
    agent_version: str = "triage-rules-v1"


# -----------------------------------------
# 3. BUG CATEGORY DETECTION
# -----------------------------------------

CATEGORY_RULES = {
    "Security": [
        r"sql injection",
        r"xss",
        r"cross.site scripting",
        r"csrf",
        r"unauthorized access",
        r"authentication bypass",
        r"privilege escalation",
        r"data breach",
        r"remote code execution",
        r"credential leak"
    ],

    "Performance": [
        r"slow",
        r"latency",
        r"timeout",
        r"memory leak",
        r"out of memory",
        r"high cpu",
        r"deadlock",
        r"performance",
        r"freezes",
        r"unresponsive"
    ],

    "UI": [
        r"layout",
        r"css",
        r"button",
        r"dropdown",
        r"rendering",
        r"alignment",
        r"display issue",
        r"visual",
        r"overlapping"
    ],

    "Compatibility": [
        r"browser compatibility",
        r"cross.browser",
        r"incompatible",
        r"version mismatch",
        r"operating system",
        r"device compatibility"
    ]
}


# -----------------------------------------
# 4. AFFECTED COMPONENT DETECTION
# -----------------------------------------

COMPONENT_RULES = {
    "Authentication": [
        r"\blogin\b", r"\bsign in\b", r"\blogout\b",
        r"\bpassword\b", r"\bauthentication\b",
        r"\bauthorization\b", r"\btoken\b", r"\bsession\b"
    ],

    "Database": [
        r"\bdatabase\b", r"\bsql\b", r"\bsqlite\b",
        r"\bpostgres\b", r"\bmysql\b", r"\bmongodb\b",
        r"\bquery\b", r"\btransaction\b", r"\bmigration\b"
    ],

    "File / Storage": [
        r"\bfile\b", r"\bfiles\b", r"\bupload\b",
        r"\bdownload\b", r"\battachment\b",
        r"\bstorage\b", r"\bdirectory\b",
        r"\bdocument\b"
    ],

    "Build / Deployment": [
        r"\bbuild\b", r"\bcompil(?:e|es|ed|ing|ation)\b",
        r"\bdeployment\b", r"\bdocker\b",
        r"\bcontainer\b", r"\bpipeline\b",
        r"\bdependency\b", r"\bconfiguration\b"
    ],

    "Memory / Runtime": [
        r"\bmemory\b", r"\bheap\b", r"\bstack overflow\b",
        r"\bruntime\b", r"\bcrash(?:es|ed|ing)?\b",
        r"\bsegmentation fault\b", r"\bnull pointer\b"
    ],

    "Networking": [
        r"\bnetwork\b", r"\bconnection\b", r"\bsocket\b",
        r"\bdns\b", r"\bproxy\b", r"\bssl\b", r"\btls\b"
    ],

    "Frontend / UI": [
        r"\bfrontend\b", r"\binterface\b", r"\breact\b",
        r"\bjavascript\b", r"\btypescript\b",
        r"\bhtml\b", r"\bcss\b", r"\brender(?:ing)?\b",
        r"\bbutton\b"
    ],

    "API / Backend": [
        r"\bapi\b", r"\bendpoint\b", r"\bhttp\b",
        r"\bfastapi\b", r"\bserver\b", r"\bbackend\b",
        r"\bmiddleware\b"
    ]
}


# -----------------------------------------
# 5. SEVERITY CLASSIFICATION
# -----------------------------------------

SEVERITY_RULES = {
    "Critical": [
        r"remote code execution",
        r"data breach",
        r"permanent data loss",
        r"production down",
        r"system.wide outage",
        r"complete outage",
        r"all users affected"
    ],

    "High": [
        r"application crashes",
        r"\bcrash\b",
        r"service unavailable",
        r"cannot login",
        r"cannot log in",
        r"payment failure",
        r"data corruption",
        r"security vulnerability",
        r"major functionality",
        r"blocks all"
    ],

    "Medium": [
        r"intermittent",
        r"workaround",
        r"partial failure",
        r"sometimes",
        r"incorrect result",
        r"feature not working",
        r"degraded"
    ],

    "Low": [
        r"typo",
        r"cosmetic",
        r"minor",
        r"slight",
        r"misalignment",
        r"tooltip",
        r"documentation",
        r"formatting",
        r"color issue"
    ]
}


# -----------------------------------------
# 6. PRIORITY MAPPING
# -----------------------------------------

PRIORITY_MAPPING = {
    "Critical": "P0",
    "High": "P1",
    "Medium": "P2",
    "Low": "P3"
}


def find_matches(text: str, patterns: List[str]) -> List[str]:
    matches = []

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            matches.append(match.group(0))

    return matches


# -----------------------------------------
# 7. CATEGORY CLASSIFICATION
# -----------------------------------------

def classify_category(text: str):

    for category, patterns in CATEGORY_RULES.items():

        matches = find_matches(text, patterns)

        if matches:
            return category, matches

    return "Functional", []


# -----------------------------------------
# 8. COMPONENT IDENTIFICATION
# -----------------------------------------
def identify_component(text: str):

    for component, patterns in COMPONENT_RULES.items():

        matches = find_matches(text, patterns)

        if matches:
            return component, matches

    return "Unknown", []

# -----------------------------------------
# 9. SEVERITY CLASSIFICATION
# -----------------------------------------

def classify_severity(text: str, reported_severity=None):

    for severity, patterns in SEVERITY_RULES.items():

        matches = find_matches(text, patterns)

        if matches:
            return severity, matches, "keyword_evidence"

    # Preserve submitted severity as fallback.
    severity_aliases = {
        "critical": "Critical",
        "blocker": "Critical",
        "high": "High",
        "major": "High",
        "medium": "Medium",
        "normal": "Medium",
        "low": "Low",
        "minor": "Low"
    }

    if reported_severity:

        normalized = severity_aliases.get(
            reported_severity.strip().lower()
        )

        if normalized:
            return (
                normalized,
                [f"Reported severity: {reported_severity}"],
                "reported_fallback"
            )

    return "Medium", [], "low_evidence_default"


# -----------------------------------------
# 10. MAIN TRIAGE AGENT
# -----------------------------------------

def triage_bug(bug: Any) -> TriageOutput:

    if isinstance(bug, dict):
        data = TriageInput(**bug)

    elif isinstance(bug, TriageInput):
        data = bug

    elif hasattr(bug, "model_dump"):
        data = TriageInput(**bug.model_dump())

    elif hasattr(bug, "dict"):
        data = TriageInput(**bug.dict())

    else:
        raise TypeError("Unsupported bug input format")

    title = data.title or ""
    description = data.description or ""

    text = " ".join([
    title,
    description,
    data.project_name or ""
    ]).lower()

    # Missing information detection
    missing = []

    if not title.strip():
        missing.append("title")

    if not description.strip():
        missing.append("description")

    if not data.project_name:
        missing.append("project_name")

    if not data.programming_language:
        missing.append("programming_language")

    # Classification
    category, category_hits = classify_category(text)

    component, component_hits = identify_component(text)

    severity, severity_hits, severity_source = classify_severity(
        text,
        data.severity
    )

    priority = PRIORITY_MAPPING[severity]

    # Collect evidence
    evidence = []

    evidence.extend([
        f"Category indicator: {x}"
        for x in category_hits
    ])

    evidence.extend([
        f"Component indicator: {x}"
        for x in component_hits
    ])

    evidence.extend([
        f"Severity indicator: {x}"
        for x in severity_hits
    ])

    # -------------------------------------
    # 11. CONFIDENCE SCORING
    # -------------------------------------

    confidence = 0.35

    if title.strip():
        confidence += 0.10

    if len(description.strip()) >= 40:
        confidence += 0.10

    if category_hits:
        confidence += 0.10

    if component_hits:
        confidence += 0.15

    if severity_source == "keyword_evidence":
        confidence += 0.15

    elif severity_source == "reported_fallback":
        confidence += 0.05

    if len(missing) >= 2:
        confidence -= 0.10

    confidence = round(
        max(0.20, min(0.95, confidence)),
        2
    )

    # -------------------------------------
    # 12. REASONING GENERATION
    # -------------------------------------

    reasoning = [
        f"Bug classified as {category} based on its description."
    ]

    if component != "Unknown":

        reasoning.append(
            f"{component} identified from matching technical terms."
        )

    else:

        reasoning.append(
            "Affected component could not be determined confidently."
        )

    if severity_source == "keyword_evidence":

        reasoning.append(
            f"{severity} severity selected using impact indicators: "
            + ", ".join(severity_hits)
            + "."
        )

    elif severity_source == "reported_fallback":

        reasoning.append(
            f"Reported severity {data.severity} used as fallback "
            "because stronger impact evidence was unavailable."
        )

    else:

        reasoning.append(
            "Limited impact evidence; Medium assigned as a provisional default."
        )

    reasoning.append(
        f"Priority {priority} assigned using the severity mapping."
    )

    if missing:

        reasoning.append(
            "Missing information: " + ", ".join(missing) + "."
        )

    return TriageOutput(
        bug_category=category,
        severity=severity,
        priority=priority,
        affected_component=component,
        confidence=confidence,
        reasoning=" ".join(reasoning),
        evidence=evidence,
        missing_information=missing,
        reported_severity=data.severity
    )


# -----------------------------------------
# 13. AGENT CLASS INTERFACE
# -----------------------------------------

class TriageAgent:

    def analyze(self, bug: Any) -> TriageOutput:

        return triage_bug(bug)
