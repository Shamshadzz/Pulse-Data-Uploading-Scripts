"""Repair script to restore missing PLOT row (e.g., A-16a) if its ID
is referenced by BLOCK rows but absent in the design elements CSV.

Logic:
1. Load CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv.
2. Collect all existing IDs.
3. For each BLOCK row, if its PARENT_ID is not in existing IDs, mark parent as missing.
4. If 'A-16a' PLOT row is missing and exactly one parent ID is missing, insert a new row:
   - ID = missing parent id
   - PROJECT_ID = taken from one of the BLOCK rows referencing this parent
   - NAME = 'A-16a'
   - TYPE = 'PLOT'
   - PARENT_ID = '' (empty)
5. Write a backup then rewrite the CSV with the injected PLOT row appended at end.

Safe re-run: If the PLOT already exists or no missing parent ID found, script exits without modification.
"""

import csv
from pathlib import Path
import time

BASE_PATH = Path(r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction")
CSV_PATH = BASE_PATH / "data" / "CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv"
# backups live in sibling folder so-proj-extraction/backups
BACKUP_DIR = BASE_PATH.parent / "so-proj-extraction" / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

TARGET_PLOT_NAME = "A-16a"
TARGET_PLOT_TYPE = "PLOT"


def load_rows(path: Path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames


def detect_missing_plot(rows):
    existing_ids = {r['ID'] for r in rows}
    plot_exists = any(r['TYPE'] == TARGET_PLOT_TYPE and r['NAME'] == TARGET_PLOT_NAME for r in rows)

    if plot_exists:
        return None  # Already present

    # Parent IDs referenced by BLOCK rows
    parent_counts = {}
    for r in rows:
        if r['TYPE'] == 'BLOCK':
            pid = r['PARENT_ID']
            if pid and pid not in existing_ids:
                parent_counts[pid] = parent_counts.get(pid, 0) + 1

    if not parent_counts:
        return None

    # Choose the missing parent with highest block count (expected single)
    missing_parent_id = max(parent_counts.items(), key=lambda x: x[1])[0]

    # Find a representative block row to copy PROJECT_ID
    project_id = None
    for r in rows:
        if r['TYPE'] == 'BLOCK' and r['PARENT_ID'] == missing_parent_id:
            project_id = r['PROJECT_ID']
            break

    if not project_id:
        return None

    return missing_parent_id, project_id


def write_backup(original_path: Path):
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f"DESIGNELEMENTS_before_plot_repair_{timestamp}.bak.csv"
    backup_path.write_bytes(original_path.read_bytes())
    return backup_path


def main():
    if not CSV_PATH.exists():
        print(f"❌ CSV not found: {CSV_PATH}")
        return

    rows, fieldnames = load_rows(CSV_PATH)
    result = detect_missing_plot(rows)
    if result is None:
        print("✅ No missing plot row detected or plot already present. No changes made.")
        return

    missing_parent_id, project_id = result
    print(f"🔧 Restoring missing PLOT row for {TARGET_PLOT_NAME} with ID {missing_parent_id}")
    backup = write_backup(CSV_PATH)
    print(f"   Backup written: {backup.name}")

    new_row = {
        'ID': missing_parent_id,
        'PROJECT_ID': project_id,
        'NAME': TARGET_PLOT_NAME,
        'TYPE': TARGET_PLOT_TYPE,
        'PARENT_ID': ''
    }

    # Append new row at end (simpler; order not critical for hierarchy)
    rows.append(new_row)

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("✅ Missing plot row inserted.")
    print("   Total rows now:", len(rows))


if __name__ == '__main__':
    main()
