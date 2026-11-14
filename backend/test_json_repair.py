
import sqlite3
import json

DB_PATH = "data/processed/historical_bugs.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

rows = cursor.execute("""
    SELECT bug_id, comments
    FROM historical_bugs
""").fetchall()

valid = 0
repaired = 0
failed = []

for bug_id, raw in rows:

    try:
        json.loads(raw)
        valid += 1
        continue

    except json.JSONDecodeError:
        pass

    # Correct double-escaped quotation marks.
    fixed = raw.replace('\\\\\"', '\\\"')

    try:
        json.loads(fixed)
        repaired += 1

    except json.JSONDecodeError:
        failed.append(bug_id)

print("\n==============================")
print("JSON REPAIR TEST")
print("==============================")
print("Initially valid:", valid)
print("Successfully repaired:", repaired)
print("Still invalid:", len(failed))
print("Failed bug IDs:", failed[:20])

# Display recovered comments from first bug.
test_raw = cursor.execute("""
    SELECT comments FROM historical_bugs
    WHERE bug_id = '82174'
""").fetchone()[0]

fixed = test_raw.replace('\\\\\"', '\\\"')
data = json.loads(fixed)

print("\nRECOVERED COMMENTS:")

for comment in data.get("comments", []):
    print("-", comment.get("text", ""))

conn.close()
