"""Check for existing PLOT entries in DESIGNELEMENTS.csv."""
import csv

data = list(csv.DictReader(open('data/CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv', encoding='utf-8')))
plots = [r for r in data if r['TYPE'] == 'PLOT']

print(f'Total PLOT entries in DESIGNELEMENTS.csv: {len(plots)}')
print('\nExisting PLOT entries for our 4 target plots:')

target_projects = {
    'e0c901b8-3037-4bc1-885e-654f92aa4d1d': 'A-16a',
    'c9ce1fed-043f-4f41-92df-856028a07580': 'A-16b',
    'd2645c47-02aa-4fb5-8d19-5aabf00358c7': 'A-16c',
    'a45b536a-057b-491e-9759-42430dd20112': 'A-16d'
}

found_plots = []
for plot in plots:
    if plot['PROJECT_ID'] in target_projects:
        found_plots.append(plot)
        expected_name = target_projects[plot['PROJECT_ID']]
        print(f"\n  ✅ {plot['NAME']} (Expected: {expected_name})")
        print(f"     ID: {plot['ID']}")
        print(f"     PROJECT_ID: {plot['PROJECT_ID']}")
        print(f"     PARENT_ID: '{plot['PARENT_ID']}'")

print(f"\n{'='*80}")
if len(found_plots) == 4:
    print("🎯 Result: ALL 4 PLOT entries ALREADY EXIST in DESIGNELEMENTS.csv")
    print("\n📋 Recommendation: REUSE existing PLOT IDs as PARENT_ID for BLOCK elements")
    print("   - Do NOT create new PLOT entries")
    print("   - Use existing PLOT IDs for PARENT_ID references")
    print("   - Only create BLOCK, TABLE, and INVERTER entries")
else:
    print(f"⚠️  Result: Only {len(found_plots)}/4 PLOT entries exist")
    print("\n📋 Recommendation: CREATE missing PLOT entries")
    print(f"   - Reuse existing {len(found_plots)} PLOT IDs")
    print(f"   - Create {4 - len(found_plots)} new PLOT entries")

# Check new_design_elements.csv
print(f"\n{'='*80}")
print("Checking new_design_elements.csv for comparison:")
new_data = list(csv.DictReader(open('output/new_design_elements.csv', encoding='utf-8')))
new_plots = [r for r in new_data if r['TYPE'] == 'PLOT']
print(f"   New PLOT entries created: {len(new_plots)}")
if new_plots:
    print("\n   Currently created PLOTs:")
    for plot in new_plots:
        print(f"      - {plot['NAME']} (ID: {plot['ID']})")
