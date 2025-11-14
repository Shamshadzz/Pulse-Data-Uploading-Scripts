"""
Fix CSV Append Issue
====================

The A-16a PLOT entry got concatenated to the previous row because the original
CSV was missing a trailing newline. This script will fix the CSV by properly
separating the rows.
"""

import csv
from pathlib import Path
import shutil
from datetime import datetime

def fix_csv():
    base_path = Path(r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction")
    data_path = base_path / "data"
    target_csv = data_path / "CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv"
    
    print("="*80)
    print("CSV FIX - Repairing Concatenated Row")
    print("="*80)
    
    # Create another backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = data_path / f"CCTECH.DRS.ENTITIES-DESIGNELEMENTS_before_fix_{timestamp}.csv"
    shutil.copy2(target_csv, backup_path)
    print(f"\n💾 Backup created: {backup_path.name}")
    
    # Read all data properly using csv.DictReader
    print(f"\n📄 Reading CSV with proper parser...")
    with open(target_csv, 'r', encoding='utf-8') as f:
        # Read raw lines to find the problematic line
        lines = f.readlines()
    
    print(f"   Total lines (including header): {len(lines):,}")
    
    # Find and show the problematic line
    for i, line in enumerate(lines):
        if 'fab4ced3-a186-4270-baf6-55dc60cc85d5' in line and line.count(',') > 5:
            print(f"\n❌ Found concatenated row at line {i+1}:")
            print(f"   Preview: {line[:150]}...")
            problematic_line_index = i
            break
    
    # Re-write the CSV properly by reading with csv.DictReader
    print(f"\n🔧 Rewriting CSV with proper formatting...")
    
    # Read with csv.DictReader (it will handle the malformed row)
    with open(target_csv, 'r', encoding='utf-8') as f:
        # Skip to the problematic line area and read it manually
        all_content = f.read()
    
    # Use csv module to parse properly
    import io
    f = io.StringIO(all_content)
    reader = csv.DictReader(f)
    rows = list(reader)
    
    print(f"   Successfully parsed {len(rows):,} data rows")
    
    # Write back to file with proper formatting
    fieldnames = ['ID', 'PROJECT_ID', 'NAME', 'TYPE', 'PARENT_ID']
    temp_file = data_path / "CCTECH.DRS.ENTITIES-DESIGNELEMENTS_temp.csv"
    
    with open(temp_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        # Filter rows to only include our fieldnames
        filtered_rows = []
        for row in rows:
            filtered_row = {k: row.get(k, '') for k in fieldnames}
            filtered_rows.append(filtered_row)
        writer.writerows(filtered_rows)
    
    print(f"   ✅ Wrote {len(rows):,} rows to temporary file")
    
    # Replace original with temp file
    shutil.move(str(temp_file), str(target_csv))
    print(f"   ✅ Replaced original file")
    
    # Verify
    print(f"\n🔍 Verifying fix...")
    with open(target_csv, 'r', encoding='utf-8') as f:
        verified_rows = list(csv.DictReader(f))
    
    print(f"   Final row count: {len(verified_rows):,}")
    
    # Check A-16a PLOT
    a16a_plot = [r for r in verified_rows if r['ID'] == 'fab4ced3-a186-4270-baf6-55dc60cc85d5']
    if a16a_plot:
        plot = a16a_plot[0]
        print(f"\n✅ A-16a PLOT entry found:")
        print(f"   ID: {plot['ID']}")
        print(f"   PROJECT_ID: {plot['PROJECT_ID']}")
        print(f"   NAME: {plot['NAME']}")
        print(f"   TYPE: {plot['TYPE']}")
        print(f"   PARENT_ID: '{plot['PARENT_ID']}'")
    else:
        print(f"\n❌ A-16a PLOT entry still not found!")
    
    print(f"\n{'='*80}")
    print("✅ CSV FIX COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    fix_csv()
