
import sqlite3
import json

DB_PATH = "data/processed/historical_bugs.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

rows = cursor.execute("""
    SELECT bug_id, comments
    FROM historical_bugs
""").fetchall()

print("\n========== INVALID JSON ANALYSIS ==========\n")

count = 0

for bug_id, raw in rows:

    try:
        json.loads(raw)
        continue

    except json.JSONDecodeError:
        fixed = raw.replace('\\\\\"', '\\\"')

    try:
        json.loads(fixed)
        continue

    except json.JSONDecodeError as error:

        count += 1

        print("\nBUG ID:", bug_id)
        print("ERROR:", error.msg)
        print("POSITION:", error.pos)

        start = max(0, error.pos - 100)
        end = min(len(fixed), error.pos + 100)

        print("CONTEXT:")
        print(repr(fixed[start:end]))

        if count >= 10:
            break

print("\n==========================================")
print("Inspected invalid records:", count)

conn.close()
