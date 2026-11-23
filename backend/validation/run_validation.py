
import csv
import json
import sys

from pathlib import Path
from datetime import datetime, timezone

# Add backend root directory to Python import path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from agents.triage_agent import triage_bug
from agents.log_analysis_agent import analyze_logs


BASE_DIR = Path(__file__).resolve().parent
DATASET_FILE = BASE_DIR / "validation_dataset.json"
OUTPUT_DIR = BASE_DIR
REPORT_DIR = BASE_DIR.parent / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def model_to_dict(result):
    """Convert a Pydantic model into a normal dictionary."""
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result.dict()


def calculate_metric(results, expected_key, actual_key):
    applicable = [
        item for item in results
        if item["expected"].get(expected_key) is not None
    ]

    if not applicable:
        return {
            "correct": 0,
            "total": 0,
            "accuracy_percent": None
        }

    correct = sum(
        item["expected"].get(expected_key)
        == item["actual"].get(actual_key)
        for item in applicable
    )

    return {
        "correct": correct,
        "total": len(applicable),
        "accuracy_percent": round(
            correct / len(applicable) * 100, 2
        )
    }


def calculate_nullable_metric(results, expected_key, actual_key):
    """Compare values including expected None values."""
    total = len(results)

    correct = sum(
        item["expected"].get(expected_key)
        == item["actual"].get(actual_key)
        for item in results
    )

    return {
        "correct": correct,
        "total": total,
        "accuracy_percent": round(correct / total * 100, 2)
        if total else 0
    }


def generate_markdown(summary, results):
    metrics = summary["metrics"]

    lines = [
        "# M2.4 - Agent Validation Report",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## 1. Validation Overview",
        "",
        f"- Total test cases: {summary['total_test_cases']}",
        f"- Triage Agent successful executions: "
        f"{summary['triage_success_count']}",
        f"- Log Analysis Agent successful executions: "
        f"{summary['log_analysis_success_count']}",
        f"- Both agents successful: {summary['both_agents_success_count']}",
        f"- Both-agent execution success rate: "
        f"{summary['both_agents_success_rate']}%",
        "",
        "## 2. Accuracy Metrics",
        "",
        "| Metric | Correct | Total | Accuracy |",
        "|---|---:|---:|---:|"
    ]

    for name, value in metrics.items():
        accuracy = value["accuracy_percent"]
        accuracy_text = (
            f"{accuracy}%"
            if accuracy is not None else "N/A"
        )
        lines.append(
            f"| {name} | {value['correct']} | "
            f"{value['total']} | {accuracy_text} |"
        )

    lines.extend([
        "",
        "## 3. Test Case Results",
        "",
        "| Test ID | Test Case | Triage | Log Analysis | Result |",
        "|---|---|---|---|---|"
    ])

    for item in results:
        triage_status = (
            "PASS" if item["triage_success"] else "ERROR"
        )
        log_status = (
            "PASS" if item["log_analysis_success"] else "ERROR"
        )

        result_status = (
            "PASS" if item["all_expected_checks_pass"] else "REVIEW"
        )

        lines.append(
            f"| {item['test_id']} | {item['name']} | "
            f"{triage_status} | {log_status} | {result_status} |"
        )

    lines.extend([
        "",
        "## 4. Validation Notes",
        "",
        "- Expected labels were defined manually for this test dataset.",
        "- Accuracy is calculated by comparing actual agent outputs "
        "against expected labels.",
        "- Nullable exception and failure-location checks include "
        "cases where no exception or location is expected.",
        "- Confidence values are heuristic scores, not calibrated "
        "probabilities.",
        "- This validation measures rule-based agent behavior. "
        "It does not establish generalization to all software defects.",
        "- Successful direct execution of both agents is measured "
        "separately from the FastAPI integration test.",
        "",
        "## 5. Cases Requiring Review",
        ""
    ])

    review_cases = [
        item for item in results
        if not item["all_expected_checks_pass"]
    ]

    if review_cases:
        for item in review_cases:
            lines.append(
                f"- **{item['test_id']} - {item['name']}**"
            )
            for mismatch in item["mismatches"]:
                lines.append(f"  - {mismatch}")
            if item["triage_error"]:
                lines.append(f"  - Triage error: {item['triage_error']}")
            if item["log_analysis_error"]:
                lines.append(
                    f"  - Log analysis error: "
                    f"{item['log_analysis_error']}"
                )
    else:
        lines.append("No mismatches were detected.")

    lines.extend([
        "",
        "## 6. Conclusion",
        "",
        "The results above show the observed performance of the "
        "current Triage Agent and Log Analysis Agent on the defined "
        "validation dataset. Review mismatches before treating the "
        "system as ready for broader use.",
        ""
    ])

    return "\n".join(lines)


def generate_pdf(summary, results, pdf_path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
    except ImportError:
        print("PDF not generated. Install reportlab using:")
        print("python -m pip install reportlab")
        return False

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    story = [
        Paragraph("M2.4 - Agent Validation Report", styles["Title"]),
        Spacer(1, 8),
        Paragraph(
            f"Generated: {summary['generated_at']}",
            styles["Normal"]
        ),
        Spacer(1, 10),
        Paragraph("1. Validation Overview", styles["Heading2"])
    ]

    overview_data = [
        ["Total cases", "Triage successful", "Log successful",
         "Both successful", "Success rate"],
        [
            str(summary["total_test_cases"]),
            str(summary["triage_success_count"]),
            str(summary["log_analysis_success_count"]),
            str(summary["both_agents_success_count"]),
            f"{summary['both_agents_success_rate']}%"
        ]
    ]

    overview_table = Table(overview_data, repeatRows=1)
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))
    story.extend([overview_table, Spacer(1, 12)])

    story.append(Paragraph("2. Accuracy Metrics", styles["Heading2"]))

    metric_data = [["Metric", "Correct", "Total", "Accuracy"]]
    for name, value in summary["metrics"].items():
        accuracy = value["accuracy_percent"]
        metric_data.append([
            name,
            str(value["correct"]),
            str(value["total"]),
            f"{accuracy}%" if accuracy is not None else "N/A"
        ])

    metric_table = Table(metric_data, repeatRows=1)
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6)
    ]))
    story.extend([metric_table, Spacer(1, 12)])

    story.append(Paragraph("3. Test Case Results", styles["Heading2"]))

    test_data = [[
        "Test ID", "Test Case", "Triage", "Log Analysis", "Checks"
    ]]

    for item in results:
        test_data.append([
            item["test_id"],
            Paragraph(item["name"], styles["BodyText"]),
            "OK" if item["triage_success"] else "ERROR",
            "OK" if item["log_analysis_success"] else "ERROR",
            "PASS" if item["all_expected_checks_pass"] else "REVIEW"
        ])

    test_table = Table(
        test_data,
        repeatRows=1,
        colWidths=[22 * mm, 85 * mm, 25 * mm, 32 * mm, 25 * mm]
    )
    test_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5)
    ]))
    story.extend([test_table, Spacer(1, 12)])

    story.append(Paragraph("4. Validation Notes", styles["Heading2"]))
    notes = [
        "Expected labels were manually defined for this dataset.",
        "Accuracy is measured by comparing actual outputs with expected outputs.",
        "Confidence scores are heuristic and are not calibrated probabilities.",
        "This report evaluates rule-based behavior on these test cases only."
    ]

    for note in notes:
        story.append(Paragraph("- " + note, styles["BodyText"]))
        story.append(Spacer(1, 4))

    document.build(story)
    return True


def main():
    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    results = []

    for test in dataset:
        bug = test["input"]
        expected = test["expected"]

        triage_output = {}
        log_output = {}
        triage_error = None
        log_error = None

        try:
            triage_output = model_to_dict(triage_bug(bug))
            triage_success = True
        except Exception as error:
            triage_success = False
            triage_error = str(error)

        try:
            log_output = model_to_dict(analyze_logs(bug))
            log_analysis_success = True
        except Exception as error:
            log_analysis_success = False
            log_error = str(error)

        actual = {
            **triage_output,
            "exception_type": log_output.get("exception_type"),
            "error_message": log_output.get("error_message"),
            "failure_file": log_output.get("failure_file"),
            "line_number": log_output.get("line_number"),
            "log_confidence": log_output.get("confidence"),
            "log_missing_information": log_output.get(
                "missing_information", []
            )
        }

        checks = [
            ("bug_category", "bug_category"),
            ("severity", "severity"),
            ("priority", "priority"),
            ("affected_component", "affected_component"),
            ("exception_type", "exception_type"),
            ("failure_file", "failure_file"),
            ("line_number", "line_number")
        ]

        mismatches = []

        for expected_key, actual_key in checks:
            if expected.get(expected_key) != actual.get(actual_key):
                mismatches.append(
                    f"{expected_key}: expected "
                    f"{expected.get(expected_key)!r}, got "
                    f"{actual.get(actual_key)!r}"
                )

        all_checks_pass = (
            triage_success
            and log_analysis_success
            and len(mismatches) == 0
        )

        results.append({
            "test_id": test["test_id"],
            "name": test["name"],
            "expected": expected,
            "actual": actual,
            "triage_success": triage_success,
            "log_analysis_success": log_analysis_success,
            "triage_error": triage_error,
            "log_analysis_error": log_error,
            "mismatches": mismatches,
            "all_expected_checks_pass": all_checks_pass
        })

    total = len(results)
    triage_count = sum(item["triage_success"] for item in results)
    log_count = sum(
        item["log_analysis_success"] for item in results
    )
    both_count = sum(
        item["triage_success"] and item["log_analysis_success"]
        for item in results
    )

    metrics = {
        "Bug category accuracy": calculate_metric(
            results, "bug_category", "bug_category"
        ),
        "Severity accuracy": calculate_metric(
            results, "severity", "severity"
        ),
        "Priority accuracy": calculate_metric(
            results, "priority", "priority"
        ),
        "Affected component accuracy": calculate_metric(
            results, "affected_component", "affected_component"
        ),
        "Exception detection accuracy": calculate_nullable_metric(
            results, "exception_type", "exception_type"
        ),
        "Failure location file accuracy": calculate_nullable_metric(
            results, "failure_file", "failure_file"
        ),
        "Failure location line accuracy": calculate_nullable_metric(
            results, "line_number", "line_number"
        )
    }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_test_cases": total,
        "triage_success_count": triage_count,
        "log_analysis_success_count": log_count,
        "both_agents_success_count": both_count,
        "both_agents_success_rate": round(
            both_count / total * 100, 2
        ) if total else 0,
        "expected_checks_passed": sum(
            item["all_expected_checks_pass"] for item in results
        ),
        "expected_checks_failed": sum(
            not item["all_expected_checks_pass"] for item in results
        ),
        "metrics": metrics
    }

    # JSON detailed results
    results_json = OUTPUT_DIR / "validation_results.json"
    with open(results_json, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    # JSON summary
    summary_json = OUTPUT_DIR / "validation_summary.json"
    with open(summary_json, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4, ensure_ascii=False)

    # CSV results
    results_csv = OUTPUT_DIR / "validation_results.csv"
    with open(results_csv, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "test_id",
                "name",
                "triage_success",
                "log_analysis_success",
                "expected_checks_pass",
                "expected_severity",
                "actual_severity",
                "expected_priority",
                "actual_priority",
                "expected_component",
                "actual_component",
                "expected_exception",
                "actual_exception",
                "expected_failure_file",
                "actual_failure_file",
                "expected_line",
                "actual_line",
                "mismatches"
            ]
        )

        writer.writeheader()

        for item in results:
            expected = item["expected"]
            actual = item["actual"]

            writer.writerow({
                "test_id": item["test_id"],
                "name": item["name"],
                "triage_success": item["triage_success"],
                "log_analysis_success": item["log_analysis_success"],
                "expected_checks_pass": item["all_expected_checks_pass"],
                "expected_severity": expected.get("severity"),
                "actual_severity": actual.get("severity"),
                "expected_priority": expected.get("priority"),
                "actual_priority": actual.get("priority"),
                "expected_component": expected.get("affected_component"),
                "actual_component": actual.get("affected_component"),
                "expected_exception": expected.get("exception_type"),
                "actual_exception": actual.get("exception_type"),
                "expected_failure_file": expected.get("failure_file"),
                "actual_failure_file": actual.get("failure_file"),
                "expected_line": expected.get("line_number"),
                "actual_line": actual.get("line_number"),
                "mismatches": "; ".join(item["mismatches"])
            })

    # Markdown report
    markdown_path = REPORT_DIR / "M2.4_Validation_Report.md"
    markdown_path.write_text(
        generate_markdown(summary, results),
        encoding="utf-8"
    )

    # PDF report
    pdf_path = REPORT_DIR / "M2.4_Validation_Report.pdf"
    pdf_created = generate_pdf(summary, results, pdf_path)

    print("\n========== M2.4 VALIDATION SUMMARY ==========")
    print(f"Total test cases: {total}")
    print(f"Triage Agent successful: {triage_count}/{total}")
    print(f"Log Analysis Agent successful: {log_count}/{total}")
    print(f"Both agents successful: {both_count}/{total}")
    print(
        "Both-agent execution success rate: "
        f"{summary['both_agents_success_rate']}%"
    )
    print(
        "All expected checks passed: "
        f"{summary['expected_checks_passed']}/{total}"
    )

    print("\nAccuracy metrics:")
    for name, value in metrics.items():
        print(
            f"{name}: {value['correct']}/{value['total']} "
            f"({value['accuracy_percent']}%)"
        )

    print("\nCases requiring review:")
    review_cases = [
        item for item in results
        if not item["all_expected_checks_pass"]
    ]

    if review_cases:
        for item in review_cases:
            print(f"\n{item['test_id']} - {item['name']}")
            for mismatch in item["mismatches"]:
                print("  -", mismatch)
            if item["triage_error"]:
                print("  - Triage error:", item["triage_error"])
            if item["log_analysis_error"]:
                print("  - Log analysis error:", item["log_analysis_error"])
    else:
        print("None")

    print("\nGenerated files:")
    print(results_json)
    print(summary_json)
    print(results_csv)
    print(markdown_path)
    if pdf_created:
        print(pdf_path)


if __name__ == "__main__":
    main()
