
import sqlite3
import re
import json
import hashlib

DB_PATH = "data/processed/historical_bugs.db"

CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250


def split_text(text):
    if not text:
        return []

    text = text.strip()
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start, end)

            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - CHUNK_OVERLAP)

    return chunks

def extract_comment_text(raw_comments):
    if not raw_comments:
        return ""

    raw_comments = str(raw_comments).strip()

    # First attempt: standard JSON.
    try:
        data = json.loads(raw_comments)

    except json.JSONDecodeError:

        # Second attempt: repair double-escaped quotes.
        fixed = raw_comments.replace('\\\\\"', '\\\"')

        try:
            data = json.loads(fixed)

        except json.JSONDecodeError:

            # Third case: content is already plain text.
            return raw_comments

    extracted = []

    def collect(item):

        if isinstance(item, dict):

            comment = item.get("text")

            if isinstance(comment, str) and comment.strip():
                extracted.append(comment.strip())

            for key, value in item.items():

                if key != "text" and isinstance(value, (dict, list)):
                    collect(value)

        elif isinstance(item, list):

            for element in item:
                collect(element)

    collect(data)

    return "\n\n".join(dict.fromkeys(extracted))



def extract_stack_traces(text):

    if not text:
        return ""

    lines = text.splitlines()
    matches = []

    patterns = [
        r"(?i)\bexception\b",
        r"(?i)\berror\b",
        r"(?i)\bcaused by:",
        r"^\s*at\s+[\w.$<>]+\(",
        r"^\s*File\s+.*line\s+\d+",
        r"^\s*Traceback",
        r"^\s*\.{3}\s+\d+\s+more",
    ]

    capture = False
    trace_block = []

    for line in lines:

        stripped = line.strip()

        if any(re.search(p, stripped) for p in patterns):

            capture = True
            trace_block.append(stripped)

        elif capture and (
            stripped.startswith("at ")
            or stripped.startswith("...")
            or stripped.startswith("File ")
        ):

            trace_block.append(stripped)

        else:

            if trace_block:
                matches.extend(trace_block)
                trace_block = []

            capture = False

    if trace_block:
        matches.extend(trace_block)

    return "\n".join(dict.fromkeys(matches))


def create_chunks():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bug_chunks (
            chunk_id TEXT PRIMARY KEY,
            bug_id TEXT,
            source TEXT,
            project TEXT,
            component TEXT,
            chunk_type TEXT,
            chunk_text TEXT
        )
    """)

    # Rebuild chunks from the source bug table.
    cursor.execute("DELETE FROM bug_chunks")

    cursor.execute("""
        SELECT bug_id, source, project, component,
               summary, description, comments, resolution
        FROM historical_bugs
    """)

    bugs = cursor.fetchall()

    total_chunks = 0
    chunk_types = {}

    for bug in bugs:

        (
            bug_id, source, project, component,
            summary, description, raw_comments, resolution
        ) = bug

        comments = extract_comment_text(raw_comments)

        sections = {

            "description": (
                f"Summary: {summary or ''}\n"
                f"Description: {description or ''}"
            ),

            "comments": comments,

        }

        # Extract stack traces from descriptions and comments.
        combined_text = "\n".join([
            description or "",
            comments
        ])

        stack_trace = extract_stack_traces(combined_text)

        if stack_trace:
            sections["stack_trace"] = stack_trace

        for chunk_type, section_text in sections.items():

            for index, chunk in enumerate(
                split_text(section_text)
            ):

                unique_text = (
                    f"{bug_id}|{chunk_type}|{index}|{chunk}"
                )

                chunk_id = hashlib.sha256(
                    unique_text.encode("utf-8")
                ).hexdigest()

                cursor.execute("""
                    INSERT INTO bug_chunks
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id,
                    bug_id,
                    source,
                    project,
                    component,
                    chunk_type,
                    chunk
                ))

                total_chunks += 1

                chunk_types[chunk_type] = (
                    chunk_types.get(chunk_type, 0) + 1
                )

    conn.commit()
    conn.close()

    print("\n================================")
    print("BUG CHUNKING COMPLETED")
    print("================================")

    print("Historical bugs:", len(bugs))
    print("Total chunks:", total_chunks)

    for name, count in chunk_types.items():
        print(f"{name}: {count}")

    print("Database table: bug_chunks")
    print("================================")


if __name__ == "__main__":
    create_chunks()
