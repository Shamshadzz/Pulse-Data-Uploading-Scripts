import csv
from pathlib import Path
from typing import Dict, List, Any


def list_csv_headers(data_dir: Path) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for p in sorted(data_dir.glob('*.csv')):
        # Expect names like CCTECH.DRS.ENTITIES-<ENTITY>.csv
        name = p.stem
        if '-' in name:
            ent = name.split('-')[-1]
        else:
            ent = name
        try:
            with p.open('r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
        except StopIteration:
            header = []
        results[ent] = {
            'file': str(p),
            'columns': header,
        }
    return results
