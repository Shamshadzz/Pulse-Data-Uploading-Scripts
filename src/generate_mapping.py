"""
Generate smart mapping.yaml from schema and Excel workbook.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from src.introspect_excel import introspect_workbook


def fuzzy_match_column(csv_field: str, excel_headers: List[str]) -> str | None:
    """Try to find Excel column matching CSV field name."""
    # Normalize for comparison
    csv_norm = csv_field.upper().replace('_', ' ').strip()
    
    # Exact match
    for h in excel_headers:
        h_norm = h.upper().replace('_', ' ').strip()
        if h_norm == csv_norm:
            return h
    
    # Contains match
    for h in excel_headers:
        h_norm = h.upper().replace('_', ' ').strip()
        if csv_norm in h_norm or h_norm in csv_norm:
            return h
    
    # Partial word match
    csv_words = set(csv_norm.split())
    best_match = None
    best_score = 0
    for h in excel_headers:
        h_words = set(h.upper().replace('_', ' ').split())
        common = csv_words & h_words
        if len(common) > best_score:
            best_score = len(common)
            best_match = h
    
    if best_score >= 1:
        return best_match
    
    return None


def infer_lookup_key(target_entity: str, schema: Dict[str, Any]) -> str:
    """Infer natural key field for FK lookup."""
    entity_info = schema['entities'].get(target_entity, {})
    
    # Check unique constraints first
    for uc in entity_info.get('uniqueConstraints', []):
        cols = uc.get('columns', [])
        if len(cols) == 1:
            return cols[0]
    
    # Common patterns
    for field in entity_info.get('fields', []):
        fname = field['name']
        if fname in ['CODE', 'NAME', 'SO_NUMBER', 'EMAIL']:
            return fname
    
    # Default to NAME if exists
    field_names = [f['name'] for f in entity_info.get('fields', [])]
    if 'NAME' in field_names:
        return 'NAME'
    if 'CODE' in field_names:
        return 'CODE'
    
    return 'ID'  # fallback


def generate_mapping_yaml(schema_path: Path, workbook_path: Path, output_path: Path) -> None:
    """Generate mapping.yaml with FK lookups and column mappings."""
    
    # Load schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    # Introspect Excel with multi-row headers
    excel_info = introspect_workbook(str(workbook_path), header_rows=3)
    
    print(f"Found {len(excel_info['sheets'])} sheet(s) in workbook:")
    for s in excel_info['sheets']:
        print(f"  - {s['name']}: {len(s['headers'])} columns")
    print()
    
    # Since there's only one sheet, we'll map it to multiple entities logically
    # The sheet appears to contain project/SO data
    main_sheet = excel_info['sheets'][0]
    sheet_name = main_sheet['name']
    headers = main_sheet['headers']
    
    print(f"Excel merged headers:")
    for idx, h in enumerate(headers, 1):
        if h:
            print(f"  [{idx:2d}] {h}")
    print()
    
    # Define entity priorities in ingestion order
    entities_to_map = schema.get('ingestionOrder', [])
    
    lines = [
        "# Auto-generated mapping configuration",
        "# Single sheet contains multiple entity data - we'll process in dependency order",
        "",
        "version: 1",
        f'workbook: "{excel_info["workbook"]}"',
        "mode: append-only",
        "",
        "# The single sheet contains project/service order data",
        "# We extract different entities from the same sheet by mapping relevant columns",
        "",
        "sheets:",
    ]
    
    # Map key entities based on actual Excel columns
    # Build smart entity configs based on what columns exist
    key_entities = {}
    
    # CLUSTERS
    if 'Cluster' in headers:
        key_entities['CLUSTERS'] = {
            'columns': {'Cluster': 'NAME'}
        }
    
    # LOCATIONS
    if 'Location' in headers:
        key_entities['LOCATIONS'] = {
            'columns': {'Location': 'NAME'},
            'fks': {'CLUSTER_ID': {'entity': 'CLUSTERS', 'match_field': 'NAME', 'from': 'Cluster'}}
        }
    
    # SPVS
    if 'SPV' in headers:
        key_entities['SPVS'] = {
            'columns': {'SPV': 'NAME'}
        }
    
    # PROJECTS
    if 'Project' in headers:
        key_entities['PROJECTS'] = {
            'columns': {
                'Project': 'NAME',
                'Project Type': 'TYPE',
                'Project Category': 'CATEGORY'
            },
            'fks': {'SPV_ID': {'entity': 'SPVS', 'match_field': 'NAME', 'from': 'SPV'}}
        }
    
    # PLOTS
    if 'Plot No' in headers:
        key_entities['PLOTS'] = {
            'columns': {'Plot No': 'NAME'},
            'fks': {'LOCATION_ID': {'entity': 'LOCATIONS', 'match_field': 'NAME', 'from': 'Location'}}
        }
    
    # VENDORS
    if 'Vendor Code' in headers:
        key_entities['VENDORS'] = {
            'columns': {
                'Vendor Code': 'CODE',
                'Vendor Name': 'NAME'
            }
        }
    
    # PACKAGES
    if 'Package' in headers:
        key_entities['PACKAGES'] = {
            'columns': {'Package': 'NAME'}
        }
    
    # PROJECTDEFINITIONS
    for h in headers:
        if 'Project Definition Code' in h:
            key_entities['PROJECTDEFINITIONS'] = {
                'columns': {
                    h: 'CODE'
                },
                'fks': {'PROJECT_ID': {'entity': 'PROJECTS', 'match_field': 'NAME', 'from': 'Project'}}
            }
            break
    
    # SERVICEORDERS
    for h in headers:
        if 'SO Number' in h:
            key_entities['SERVICEORDERS'] = {
                'columns': {
                    h: 'SO_NUMBER',
                    'Package': 'HEADER_TEXT'
                },
                'fks': {
                    'PROJECT_ID': {'entity': 'PROJECTS', 'match_field': 'NAME', 'from': 'Project'},
                    'VENDOR_ID': {'entity': 'VENDORS', 'match_field': 'CODE', 'from': 'Vendor Code'}
                }
            }
            break
    
    for entity in entities_to_map:
        if entity not in schema['entities']:
            continue
        
        # Check if this entity appears in our key mapping
        if entity not in key_entities:
            continue
        
        entity_info = schema['entities'][entity]
        csv_info = entity_info.get('csv')
        if not csv_info:
            continue
        
        entity_config = key_entities[entity]
        id_field = entity_info.get('idField', 'ID')
        uuid_required = entity_info.get('uuidRequired', False)
        
        lines.append(f"\n  # --- {entity} ---")
        lines.append(f'  - sheet: "{sheet_name}"')
        lines.append(f"    entity: {entity}")
        lines.append(f"    csvFile: {csv_info['file']}")
        lines.append(f"    id:")
        lines.append(f"      column: {id_field}")
        lines.append(f"      uuidPolicy: {'generate_if_blank' if uuid_required else 'preserve'}")
        
        # Column mapping from entity config
        lines.append(f"    columnMap:")
        for excel_col, csv_col in entity_config.get('columns', {}).items():
            if excel_col in headers:
                lines.append(f'      "{excel_col}": {csv_col}')
        
        # FK lookups from entity config
        fk_configs = entity_config.get('fks', {})
        if fk_configs:
            lines.append(f"    lookups:")
            for fk_field, fk_def in fk_configs.items():
                target_entity = fk_def['entity']
                match_field = fk_def['match_field']
                from_col = fk_def['from']
                
                lines.append(f"      {fk_field}:")
                lines.append(f"        entity: {target_entity}")
                lines.append(f"        match:")
                lines.append(f"          - field: {match_field}")
                lines.append(f'            from: "{from_col}"')
        
        lines.append(f"    defaults: {{}}")
    
    lines.append("\ningestion:")
    lines.append("  order: auto  # use dependency order from schema.json")
    lines.append("")
    
    # Write
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ Generated: {output_path}")
    print(f"\nNext: Review the mapping, adjust TODO items, then run validation.")


if __name__ == '__main__':
    root = Path(__file__).parent.parent
    schema_path = root / 'build' / 'schema.json'
    workbook_path = root / 'Khavda Phase-3 Solar_Projects and SO Data (1).xlsx'
    output_path = root / 'config' / 'mapping_generated.yaml'
    
    if not schema_path.exists():
        print(f"ERROR: Run 'python -m src.build_schema' first", file=sys.stderr)
        sys.exit(1)
    
    if not workbook_path.exists():
        print(f"ERROR: Workbook not found: {workbook_path}", file=sys.stderr)
        sys.exit(1)
    
    generate_mapping_yaml(schema_path, workbook_path, output_path)
