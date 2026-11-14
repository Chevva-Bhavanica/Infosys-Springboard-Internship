
import sqlite3

db = sqlite3.connect("data/processed/historical_bugs.db")
cursor = db.cursor()

cursor.execute("SELECT COUNT(*) FROM historical_bugs")
print("Total bugs:", cursor.fetchone()[0])

cursor.execute("""
    SELECT bug_id, project, component, severity,
           status, summary
    FROM historical_bugs
    LIMIT 10
""")

print("\nHISTORICAL BUG RECORDS\n")

for row in cursor.fetchall():
    print("-" * 60)
    print("Bug ID:", row[0])
    print("Project:", row[1])
    print("Component:", row[2])
    print("Severity:", row[3])
    print("Status:", row[4])
    print("Summary:", row[5])

db.close()
