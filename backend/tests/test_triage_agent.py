
from agents.triage_agent import triage_bug


def test_login_bug():

    bug = {
        "title": "NullPointerException during user login",
        "description": (
            "Application crashes when a user "
            "submits the login form."
        ),
        "project_name": "BugDiagnosisTest",
        "programming_language": "Java",
        "severity": "High"
    }

    result = triage_bug(bug)

    assert result.severity == "High"
    assert result.priority == "P1"
    assert result.affected_component == "Authentication"


def test_security_bug():

    bug = {
        "title": "Remote code execution vulnerability",
        "description": (
            "An unauthenticated attacker can execute "
            "arbitrary commands."
        )
    }

    result = triage_bug(bug)

    assert result.bug_category == "Security"
    assert result.severity == "Critical"
    assert result.priority == "P0"


def test_minor_bug():

    bug = {
        "title": "Minor button alignment issue",
        "description": (
            "The submit button is slightly misaligned."
        )
    }

    result = triage_bug(bug)

    assert result.severity == "Low"
    assert result.priority == "P3"


def test_missing_information():

    result = triage_bug({
        "title": "API timeout"
    })

    assert "description" in result.missing_information
