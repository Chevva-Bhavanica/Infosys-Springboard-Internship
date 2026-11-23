
import sqlite3
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bug_reports.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bug_reports (
                bug_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                project_name TEXT,
                programming_language TEXT,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                stack_trace TEXT,
                error_logs TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                FOREIGN KEY (bug_id)
                    REFERENCES bug_reports(bug_id)
                    ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS triage_results (
                bug_id TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                analyzed_at TEXT NOT NULL,
                FOREIGN KEY (bug_id)
                    REFERENCES bug_reports(bug_id)
                    ON DELETE CASCADE
            )
        """)

        # Store combined output from all agents
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_contexts (
                bug_id TEXT PRIMARY KEY,
                context_json TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                analyzed_at TEXT NOT NULL,
                FOREIGN KEY (bug_id)
                    REFERENCES bug_reports(bug_id)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_submitted_bug_created
            ON bug_reports(created_at)
        """)

    print("Submission database initialized successfully.")
