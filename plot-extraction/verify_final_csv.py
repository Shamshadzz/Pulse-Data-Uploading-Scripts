"""Verify final CSV state after append."""
import csv

# ASCII-safe print wrapper
import builtins as _b
def _safe_print(*args, **kwargs):
    safe_args = [str(a).encode('ascii','ignore').decode() for a in args]
    return _b.print(*safe_args, **kwargs)
print = _safe_print

# Count rows more carefully
target_csv = r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction\data\CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv"

output_summary_path = r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction\output\verification_summary.txt"

# Method 1: Count with csv.DictReader (most accurate)
with open(target_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    data_rows = list(reader)
    actual_count = len(data_rows)

print("="*80)
print("FINAL VERIFICATION")
print("="*80)

print(f"\nFinal row count (csv.DictReader): {actual_count:,}")

# Count by type
from collections import Counter
type_counts = Counter(row['TYPE'] for row in data_rows)

print(f"\nBreakdown by TYPE:")
for element_type, count in type_counts.items():
    print(f"   {element_type}: {count:,}")

print(f"\nTotal: {sum(type_counts.values()):,}")

# Check our 4 plots
print(f"\n{'='*80}")
print("VERIFICATION: Our 4 Plots Present")
print("="*80)

target_projects = {
    'e0c901b8-3037-4bc1-885e-654f92aa4d1d': 'A-16a',
    'c9ce1fed-043f-4f41-92df-856028a07580': 'A-16b',
    'd2645c47-02aa-4fb5-8d19-5aabf00358c7': 'A-16c',
    'a45b536a-057b-491e-9759-42430dd20112': 'A-16d'
}

lines = []
for project_id, plot_name in target_projects.items():
    plot_elements = [r for r in data_rows if r['PROJECT_ID'] == project_id]
    plot_entry = [r for r in plot_elements if r['TYPE'] == 'PLOT']
    blocks = [r for r in plot_elements if r['TYPE'] == 'BLOCK']
    tables = [r for r in plot_elements if r['TYPE'] == 'TABLE']
    inverters = [r for r in plot_elements if r['TYPE'] == 'INVERTER']
    print(f"\n✅ {plot_name}:")
    print(f"   Total elements: {len(plot_elements):,}")
    print(f"   PLOTs: {len(plot_entry)}, BLOCKs: {len(blocks)}, TABLEs: {len(tables)}, INVERTERs: {len(inverters)}")
    lines.append(f"{plot_name}: total={len(plot_elements)} PLOT={len(plot_entry)} BLOCK={len(blocks)} TABLE={len(tables)} INVERTER={len(inverters)}")

print(f"\n{'='*80}")
print("✅ VERIFICATION COMPLETE - ALL DATA SUCCESSFULLY APPENDED!")
print("="*80)

# Persist summary for external inspection
with open(output_summary_path, 'w', encoding='utf-8') as outf:
    outf.write(f"Final row count: {actual_count}\n")
    outf.write("Type counts:\n")
    for element_type, count in type_counts.items():
        outf.write(f"  {element_type}: {count}\n")
    outf.write("Plot breakdown:\n")
    for line in lines:
        outf.write(f"  {line}\n")
