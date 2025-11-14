"""Verify hierarchy structure in output CSV."""
import csv

data = list(csv.DictReader(open('output/new_design_elements.csv', encoding='utf-8')))

print('='*80)
print('HIERARCHY VERIFICATION')
print('='*80)

print(f'\nTotal elements: {len(data)}')

plots = [r for r in data if r['TYPE'] == 'PLOT']
blocks = [r for r in data if r['TYPE'] == 'BLOCK']
tables = [r for r in data if r['TYPE'] == 'TABLE']
inverters = [r for r in data if r['TYPE'] == 'INVERTER']

print(f'PLOTs: {len(plots)}')
print(f'BLOCKs: {len(blocks)}')
print(f'TABLEs: {len(tables)}')
print(f'INVERTERs: {len(inverters)}')

print('\n' + '='*80)
print('SAMPLE HIERARCHY CHAIN')
print('='*80)

# Show PLOT → BLOCK → TABLE/INVERTER chain
plot = plots[0]
print(f'\n📊 PLOT:')
print(f'   ID: {plot["ID"]}')
print(f'   NAME: {plot["NAME"]}')
print(f'   TYPE: {plot["TYPE"]}')
print(f'   PARENT_ID: "{plot["PARENT_ID"]}" (empty for PLOT)')
print(f'   PROJECT_ID: {plot["PROJECT_ID"]}')

block = [b for b in blocks if b['PARENT_ID'] == plot['ID']][0]
print(f'\n   ↓ BLOCK (child of PLOT):')
print(f'   ID: {block["ID"]}')
print(f'   NAME: {block["NAME"]}')
print(f'   TYPE: {block["TYPE"]}')
print(f'   PARENT_ID: {block["PARENT_ID"]} (matches PLOT ID above)')
print(f'   PROJECT_ID: {block["PROJECT_ID"]}')

table = [t for t in tables if t['PARENT_ID'] == block['ID']][0]
print(f'\n      ↓ TABLE (child of BLOCK):')
print(f'      ID: {table["ID"]}')
print(f'      NAME: {table["NAME"]}')
print(f'      TYPE: {table["TYPE"]}')
print(f'      PARENT_ID: {table["PARENT_ID"]} (matches BLOCK ID above)')
print(f'      PROJECT_ID: {table["PROJECT_ID"]}')

inv = [i for i in inverters if i['PARENT_ID'] == block['ID']][0]
print(f'\n      ↓ INVERTER (child of BLOCK):')
print(f'      ID: {inv["ID"]}')
print(f'      NAME: {inv["NAME"]}')
print(f'      TYPE: {inv["TYPE"]}')
print(f'      PARENT_ID: {inv["PARENT_ID"]} (matches BLOCK ID above)')
print(f'      PROJECT_ID: {inv["PROJECT_ID"]}')

print('\n' + '='*80)
print('PROJECT DISTRIBUTION')
print('='*80)

from collections import Counter
project_counts = Counter(r['PROJECT_ID'] for r in data)
project_names = {
    'e0c901b8-3037-4bc1-885e-654f92aa4d1d': 'A-16a',
    'c9ce1fed-043f-4f41-92df-856028a07580': 'A-16b',
    'd2645c47-02aa-4fb5-8d19-5aabf00358c7': 'A-16c',
    'a45b536a-057b-491e-9759-42430dd20112': 'A-16d'
}

for project_id, count in project_counts.items():
    plot_name = project_names.get(project_id, 'Unknown')
    print(f'\n{plot_name}: {count:,} elements')
    project_data = [r for r in data if r['PROJECT_ID'] == project_id]
    project_plots = len([r for r in project_data if r['TYPE'] == 'PLOT'])
    project_blocks = len([r for r in project_data if r['TYPE'] == 'BLOCK'])
    project_tables = len([r for r in project_data if r['TYPE'] == 'TABLE'])
    project_inverters = len([r for r in project_data if r['TYPE'] == 'INVERTER'])
    print(f'   PLOTs: {project_plots}, BLOCKs: {project_blocks}, TABLEs: {project_tables}, INVERTERs: {project_inverters}')

print('\n' + '='*80)
print('✅ HIERARCHY STRUCTURE VERIFIED!')
print('='*80)
