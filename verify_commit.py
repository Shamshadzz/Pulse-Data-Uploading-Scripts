"""Verify appended data integrity."""
import csv
from pathlib import Path

entities = {
    'SPVS': ('NAME', 7),  # Expected: 3 old + 4 new = 7
    'PROJECTS': ('NAME', 10),  # Expected: 3 old + 7 new = 10
    'VENDORS': ('CODE', 64),  # Expected: 4 old + 60 new = 64
    'PROJECTDEFINITIONS': ('CODE', 11),  # Expected: 3 old + 8 new = 11
    'LOCATIONS': ('NAME', 256),  # Expected: 1 old + 255 new = 256
    'PLOTS': ('NAME', 255),  # Expected: 0 old + 255 new = 255
    'PACKAGES': ('NAME', 6),  # Expected: 3 old + 3 new = 6
}

data_dir = Path('data')

print("="*60)
print("DATA INTEGRITY VERIFICATION")
print("="*60)

for entity, (col, expected) in entities.items():
    csv_file = data_dir / f'CCTECH.DRS.ENTITIES-{entity}.csv'
    if csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            actual = len(rows)
            status = "✅" if actual == expected else "⚠️"
            
            print(f"\n{status} {entity}: {actual} rows (expected {expected})")
            
            # Show first 3 and last 3
            if actual > 0:
                print(f"  First 3:")
                for i, row in enumerate(rows[:3], 1):
                    val = row.get(col, '')
                    id_val = row.get('ID', '')[:8] if row.get('ID') else 'NO-ID'
                    print(f"    {i}. {col}={val}, ID={id_val}...")
                
                if actual > 6:
                    print(f"  ... ({actual - 6} rows) ...")
                
                if actual > 3:
                    print(f"  Last 3:")
                    for i, row in enumerate(rows[-3:], actual - 2):
                        val = row.get(col, '')
                        id_val = row.get('ID', '')[:8] if row.get('ID') else 'NO-ID'
                        print(f"    {i}. {col}={val}, ID={id_val}...")
    else:
        print(f"\n❌ {entity}: FILE NOT FOUND")

print("\n" + "="*60)
print("Backups available in: backups/")
print("="*60)
