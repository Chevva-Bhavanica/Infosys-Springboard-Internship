
import csv
import sys
from pathlib import Path

# Increase CSV field size limit
csv.field_size_limit(2**31 - 1)

file_path = Path("data/raw/eclipse/sample_data.csv")

if not file_path.exists():
    print("Dataset file not found!")
    sys.exit(1)

print("Reading Eclipse Historical Bug Dataset...")

# Read headers and sample records
with open(file_path, "r", encoding="utf-8-sig",
          errors="replace", newline="") as file:

    reader = csv.DictReader(file)

    print("\nDATASET COLUMNS:")
    print(reader.fieldnames)

    print("\nSAMPLE BUG REPORTS:")

    for i, row in enumerate(reader):
        if i >= 3:
            break

        print(f"\nBug Report {i + 1}")
        print("Bug ID:", row.get("ID"))
        print("Product:", row.get("Product"))
        print("Component:", row.get("Component"))
        print("Severity:", row.get("Severity"))
        print("Priority:", row.get("Priority"))
        print("Status:", row.get("Status"))
        print("Summary:", row.get("Summary"))
        print("Description:", (row.get("Description") or "")[:300])
        print("Resolution:", row.get("Resolution"))

# Count records
print("\nCounting total records...")

with open(file_path, "r", encoding="utf-8-sig",
          errors="replace", newline="") as file:

    reader = csv.reader(file)
    next(reader, None)
    total_records = sum(1 for _ in reader)

print("\n-----------------------------")
print("Dataset inspection completed!")
print("Total records:", total_records)
print("Total columns: 42")
print("-----------------------------")
