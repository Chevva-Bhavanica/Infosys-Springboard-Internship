
import sqlite3
import json

DB_PATH = "data/processed/historical_bugs.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

row = cursor.execute("""
    SELECT bug_id, comments
    FROM historical_bugs
    WHERE bug_id = '82174'
""").fetchone()

bug_id, raw = row

print("\nBUG ID:", bug_id)
print("RAW DATA LENGTH:", len(raw))

try:
    data = json.loads(raw)
    print("JSON STATUS: VALID")
except json.JSONDecodeError as error:
    print("JSON STATUS: INVALID")
    print("ERROR:", error)
    print("ERROR POSITION:", error.pos)

    print("\nERROR CONTEXT:")
    print(repr(raw[max(0, error.pos - 150):error.pos + 150]))

    print("\nRAW REPRESENTATION:")
    print(repr(raw[max(0, error.pos - 80):error.pos + 80]))

conn.close()
