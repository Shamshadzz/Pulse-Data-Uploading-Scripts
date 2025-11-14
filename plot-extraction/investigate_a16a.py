"""Check A-16a PLOT status."""
import csv

target_csv = r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction\data\CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv"
new_csv = r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction\output\new_design_elements.csv"

# Load both CSVs
with open(target_csv, 'r', encoding='utf-8') as f:
    all_data = list(csv.DictReader(f))

with open(new_csv, 'r', encoding='utf-8') as f:
    new_data = list(csv.DictReader(f))

a16a_project_id = 'e0c901b8-3037-4bc1-885e-654f92aa4d1d'

print("="*80)
print("A-16a PLOT Investigation")
print("="*80)

# Check new_design_elements.csv
a16a_plot_new = [r for r in new_data if r['PROJECT_ID'] == a16a_project_id and r['TYPE'] == 'PLOT']
print(f"\nIn new_design_elements.csv:")
if a16a_plot_new:
    for plot in a16a_plot_new:
        print(f"   ✅ PLOT: {plot['NAME']} (ID: {plot['ID']})")
else:
    print(f"   ❌ No PLOT found")

# Check final DESIGNELEMENTS.csv
a16a_plot_final = [r for r in all_data if r['PROJECT_ID'] == a16a_project_id and r['TYPE'] == 'PLOT']
print(f"\nIn final DESIGNELEMENTS.csv:")
if a16a_plot_final:
    for plot in a16a_plot_final:
        print(f"   ✅ PLOT: {plot['NAME']} (ID: {plot['ID']})")
else:
    print(f"   ❌ No PLOT found")

# Check all A-16a elements
a16a_all = [r for r in all_data if r['PROJECT_ID'] == a16a_project_id]
print(f"\nAll A-16a elements in final CSV: {len(a16a_all)}")
from collections import Counter
type_counts = Counter(r['TYPE'] for r in a16a_all)
for t, c in type_counts.items():
    print(f"   {t}: {c}")

# Check if PLOT was skipped due to existing entry
print(f"\n{'='*80}")
print("Checking for duplicate PLOT detection:")
print("="*80)

# Search for any PLOT with name A-16a
all_a16a_plots = [r for r in all_data if r['NAME'] == 'A-16a' and r['TYPE'] == 'PLOT']
print(f"\nAll PLOTs named 'A-16a' in DESIGNELEMENTS.csv: {len(all_a16a_plots)}")
for plot in all_a16a_plots:
    print(f"   Name: {plot['NAME']}, PROJECT_ID: {plot['PROJECT_ID']}, ID: {plot['ID']}")
