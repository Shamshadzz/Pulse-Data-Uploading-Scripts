"""
Append SOLARPROJECTATTRIBUTES and SERVICEORDERS from staging to data using proper CSV writer.
"""
import csv
from pathlib import Path

def append_csv(staging_file, data_file):
    """Append staged rows to data file using proper CSV handling."""
    # Read existing data to get headers
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing_headers = reader.fieldnames
        existing_rows = list(reader)
    
    # Read staged data
    with open(staging_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        staged_rows = list(reader)
    
    # Append staged rows to data file
    with open(data_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=existing_headers)
        for row in staged_rows:
            # Align to existing headers, fill missing with empty
            output_row = {col: row.get(col, '') for col in existing_headers}
            writer.writerow(output_row)
    
    return len(staged_rows)

if __name__ == '__main__':
    staging_dir = Path('staging')
    data_dir = Path('data')
    
    entities = [
        ('SOLARPROJECTATTRIBUTES', 'CCTECH.DRS.ENTITIES-SOLARPROJECTATTRIBUTES.csv'),
        ('SERVICEORDERS', 'CCTECH.DRS.ENTITIES-SERVICEORDERS.csv')
    ]
    
    print("Appending remaining entities...\n")
    
    for entity_name, filename in entities:
        staging_file = staging_dir / f'{entity_name}.csv'
        data_file = data_dir / filename
        
        if staging_file.exists():
            count = append_csv(staging_file, data_file)
            print(f"✓ {entity_name}: appended {count} rows → {data_file}")
        else:
            print(f"⊗ {entity_name}: staging file not found")
    
    print("\n✅ Append complete!")
