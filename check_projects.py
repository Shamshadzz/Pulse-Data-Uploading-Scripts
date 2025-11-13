"""Check staged PROJECTS structure."""
import csv

with open('staging/PROJECTS.csv') as f:
    reader = csv.DictReader(f)
    print(f"Columns: {reader.fieldnames}\n")
    rows = list(reader)
    print(f"Total rows: {len(rows)}\n")
    
    for row in rows[:5]:
        print(f"  {row['NAME']}: ID={row.get('ID','')} TYPE={row.get('TYPE','')} CATEGORY={row.get('CATEGORY','')}")
