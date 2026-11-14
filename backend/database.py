
import csv
import sqlite3
import json
import re
import html
from pathlib import Path

# File locations
CSV_FILE = Path("data/raw/eclipse/sample_data.csv")
DB_FILE = Path("data/processed/historical_bugs.db")

csv.field_size_limit(2**31 - 1)


def clean_text(value):
    """Clean and normalize text."""
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_comments(value):
    """Extract comment text without storing author information."""
    if not value:
        return ""

    try:
        data = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return clean_text(value)

    comments = []

    def collect(obj):
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key in ("text", "raw_text") and isinstance(item, str):
                    if item.strip():
                        comments.append(clean_text(item))
                elif isinstance(item, (dict, list)):
                    collect(item)

        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    collect(data)

    return "\n".join(dict.fromkeys(comments))


def create_database():
    if not CSV_FILE.exists():
        print("ERROR: Dataset CSV not found!")
        return

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    # Create historical bug table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_bugs (
            bug_id TEXT PRIMARY KEY,
            source TEXT,
            issue_url TEXT,
            project TEXT,
            component TEXT,
            version TEXT,
            platform TEXT,
            operating_system TEXT,
            status TEXT,
            resolution TEXT,
            severity TEXT,
            priority TEXT,
            summary TEXT,
            description TEXT,
            comments TEXT,
            created_at TEXT,
            updated_at TEXT,
            is_open TEXT
        )
    """)

    inserted = 0
    skipped = 0

    with open(
        CSV_FILE,
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            bug_id = clean_text(row.get("ID"))

            if not bug_id:
                skipped += 1
                continue

            record = (
                bug_id,
                "Eclipse",
                clean_text(row.get("Issue URL")),
                clean_text(row.get("Product")),
                clean_text(row.get("Component")),
                clean_text(row.get("Version")),
                clean_text(row.get("Platform")),
                clean_text(row.get("Op sys")),
                clean_text(row.get("Status")),
                clean_text(row.get("Resolution")),
                clean_text(row.get("Severity")),
                clean_text(row.get("Priority")),
                clean_text(row.get("Summary")),
                clean_text(row.get("Description")),
                extract_comments(row.get("Comments")),
                clean_text(row.get("Creation time")),
                clean_text(row.get("Last change time")),
                clean_text(row.get("Is open"))
            )

            cursor.execute("""
                INSERT OR REPLACE INTO historical_bugs
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?)
            """, record)

            inserted += 1

    # Create indexes for faster filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bug_project
        ON historical_bugs(project)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bug_severity
        ON historical_bugs(severity)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bug_status
        ON historical_bugs(status)
    """)

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM historical_bugs")
    total = cursor.fetchone()[0]

    print("\n================================")
    print("HISTORICAL BUG DATABASE CREATED")
    print("================================")
    print("Records processed:", inserted)
    print("Records skipped:", skipped)
    print("Records in database:", total)
    print("Database location:", DB_FILE)
    print("================================")

    connection.close()


if __name__ == "__main__":
    create_database()

