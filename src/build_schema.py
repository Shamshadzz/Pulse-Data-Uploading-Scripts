import json
from pathlib import Path
from typing import Dict, Any, List, Set

from src.cds_parser import parse_cds, build_dependencies, topo_sort
from src.csv_introspect import list_csv_headers


def compare_schema_to_csv(parsed: Dict[str, Any], csvs: Dict[str, Any]) -> Dict[str, Any]:
    entities = parsed['entities']
    out: Dict[str, Any] = {}
    for ename, edef in entities.items():
        # CSV file key uses entity name as in file (likely same casing)
        csv_info = csvs.get(ename, None)
        csv_columns: List[str] = csv_info['columns'] if csv_info else []

        # schema columns: include all non-association fields only
        schema_cols: List[str] = [f['name'] for f in edef.get('fields', [])]

        missing = [c for c in schema_cols if c not in csv_columns]
        extra = [c for c in csv_columns if c not in schema_cols]

        out[ename] = {
            'fields': edef.get('fields', []),
            'associations': edef.get('associations', []),
            'uniqueConstraints': edef.get('uniqueConstraints', []),
            'notes': edef.get('notes', []),
            'csv': csv_info,
            'missingInCsv': missing,
            'extraInCsv': extra,
            'idField': next((f['name'] for f in edef.get('fields', []) if f.get('key')), None),
            'uuidRequired': any(f.get('key') and f.get('type','').upper().startswith('UUID') for f in edef.get('fields', [])),
        }
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / 'schema.cds'
    data_dir = root / 'data'
    build_dir = root / 'build'
    build_dir.mkdir(exist_ok=True)

    content = schema_path.read_text(encoding='utf-8')
    parsed = parse_cds(content)

    csvs = list_csv_headers(data_dir)
    entities_report = compare_schema_to_csv(parsed, csvs)

    deps = build_dependencies(parsed)
    ingestion_order = topo_sort(deps)

    report = {
        'enums': parsed['enums'],
        'entities': entities_report,
        'dependencies': deps,
        'ingestionOrder': ingestion_order,
    }

    out_path = build_dir / 'schema.json'
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()
