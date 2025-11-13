"""Check what's in staged files."""
import csv
from pathlib import Path

staging_dir = Path('staging')
entities = ['CLUSTERS', 'LOCATIONS', 'SPVS', 'PROJECTS', 'PACKAGES', 'VENDORS', 'PROJECTDEFINITIONS']
cols = {
    'CLUSTERS': 'NAME',
    'LOCATIONS': 'NAME', 
    'SPVS': 'NAME',
    'PROJECTS': 'NAME',
    'PACKAGES': 'NAME',
    'VENDORS': 'CODE',
    'PROJECTDEFINITIONS': 'CODE'
}

for ent in entities:
    csv_file = staging_dir / f'CCTECH.DRS.ENTITIES-{ent}.csv'
    if csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            col = cols[ent]
            print(f'\n{ent}: {len(rows)} staged')
            for i, row in enumerate(rows[:5], 1):
                val = row.get(col, '')
                print(f'  {i}. {val}')
            if len(rows) > 5:
                print(f'  ... and {len(rows)-5} more')
    else:
        print(f'{ent}: NOT STAGED')
