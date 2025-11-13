"""Quick script to check existing master data."""
import csv
from pathlib import Path

master = {
    'CLUSTERS': 'NAME',
    'LOCATIONS': 'NAME', 
    'SPVS': 'NAME',
    'PROJECTS': 'NAME',
    'VENDORS': 'CODE',
    'PACKAGES': 'NAME',
    'PROJECTDEFINITIONS': 'CODE'
}

data_dir = Path('data')

for entity, col in master.items():
    csv_file = data_dir / f'CCTECH.DRS.ENTITIES-{entity}.csv'
    if csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            print(f'\n{entity} ({len(rows)} existing):')
            for i, row in enumerate(rows[:15], 1):
                val = row.get(col, '')
                print(f'  {i}. {val}')
    else:
        print(f'\n{entity}: FILE NOT FOUND')
