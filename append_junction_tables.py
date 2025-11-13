"""
Utility to append SERVICEORDERPACKAGES (skipping rows with blank packages).
"""
import csv
from pathlib import Path

def append_serviceorderpackages():
    """Append only valid SERVICEORDERPACKAGES rows (non-blank packages)."""
    staging_file = Path('staging/SERVICEORDERPACKAGES.csv')
    data_file = Path('data/CCTECH.DRS.ENTITIES-SERVICEORDERPACKAGES.csv')
    
    if not staging_file.exists():
        print(f"✗ Staging file not found: {staging_file}")
        return
    
    # Read existing data file headers
    with open(data_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
    
    # Read staged rows
    with open(staging_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        staged_rows = [row for row in reader if row.get('PACKAGE_ID')]  # Skip blank PACKAGE_ID
    
    if not staged_rows:
        print("✓ SERVICEORDERPACKAGES: No new rows to append")
        return
    
    # Append to data file
    with open(data_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        for row in staged_rows:
            # Align to data file headers
            aligned_row = {field: row.get(field, '') for field in headers}
            writer.writerow(aligned_row)
    
    print(f"✓ SERVICEORDERPACKAGES: appended {len(staged_rows)} rows → {data_file}")


if __name__ == '__main__':
    print("Appending junction table data...\n")
    append_serviceorderpackages()
    print("\n✅ Append complete!")
