
import sqlite3

conn = sqlite3.connect(
    "data/processed/historical_bugs.db"
)

cursor = conn.cursor()

cursor.execute("""
    SELECT chunk_type, COUNT(*)
    FROM bug_chunks
    GROUP BY chunk_type
""")

print("CHUNK STATISTICS")

for row in cursor.fetchall():
    print(row[0], ":", row[1])

cursor.execute("""
    SELECT bug_id, chunk_type, chunk_text
    FROM bug_chunks
    LIMIT 5
""")

print("\nSAMPLE CHUNKS")

for bug_id, chunk_type, text in cursor.fetchall():
    print("\nBug ID:", bug_id)
    print("Type:", chunk_type)
    print("Text:", text[:400])

conn.close()
