"""
Staging engine: reads Excel, transforms, validates, stages rows for CSV append.
"""
import json
import yaml
import csv
from pathlib import Path
from typing import Dict, List, Any
import openpyxl

from src.introspect_excel import introspect_workbook
from src.transformer import RowTransformer


class StagingEngine:
    """Orchestrates Excel → CSV staging pipeline."""
    
    def __init__(
        self,
        schema_path: Path,
        mapping_path: Path,
        workbook_path: Path,
        data_dir: Path,
        staging_dir: Path
    ):
        self.schema_path = schema_path
        self.mapping_path = mapping_path
        self.workbook_path = workbook_path
        self.data_dir = data_dir
        self.staging_dir = staging_dir
        
        # Load schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
        
        # Load mapping
        with open(mapping_path, 'r', encoding='utf-8') as f:
            self.mapping = yaml.safe_load(f)
        
        # Initialize transformer WITHOUT staging_dir for first pass
        self.transformer = RowTransformer(self.schema, self.mapping, data_dir)
        self.staging_dir.mkdir(exist_ok=True, parents=True)
    
    def _read_excel_data(self, sheet_name: str, header_rows: int = 3) -> List[Dict[str, Any]]:
        """
        Read data from Excel sheet starting after header rows.
        
        Returns:
            List of row dicts with merged headers as keys
        """
        # Get merged headers
        excel_info = introspect_workbook(str(self.workbook_path), header_rows=header_rows)
        sheet_info = next((s for s in excel_info['sheets'] if s['name'] == sheet_name), None)
        
        if not sheet_info:
            return []
        
        headers = sheet_info['headers']
        
        # Read data rows
        wb = openpyxl.load_workbook(str(self.workbook_path), read_only=True, data_only=True)
        ws = wb[sheet_name]
        
        rows = []
        for row_data in ws.iter_rows(min_row=header_rows + 1, values_only=True):
            if not any(row_data):  # Skip empty rows
                continue
            
            row_dict = {}
            for idx, value in enumerate(row_data):
                if idx < len(headers):
                    row_dict[headers[idx]] = value
            
            rows.append(row_dict)
        
        wb.close()
        return rows
    
    def stage_entity(self, entity: str, sheet_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage data for a single entity.
        
        Returns:
            {
                'entity': str,
                'valid_count': int,
                'error_count': int,
                'staged_file': str,
                'errors': List[...]
            }
        """
        sheet_name = sheet_config.get('sheet')
        csv_file = sheet_config.get('csvFile')
        
        if not sheet_name or not csv_file:
            return {
                'entity': entity,
                'valid_count': 0,
                'error_count': 0,
                'errors': [{'msg': 'Missing sheet or csvFile in config'}]
            }
        
        # Read Excel data
        excel_rows = self._read_excel_data(sheet_name)
        
        if not excel_rows:
            return {
                'entity': entity,
                'valid_count': 0,
                'error_count': 0,
                'errors': [{'msg': 'No data rows found in Excel'}]
            }
        
        # Transform and validate
        valid_rows, error_records = self.transformer.transform_entity(
            entity,
            sheet_config,
            excel_rows
        )
        
        # Write staged CSV
        staged_file = None
        if valid_rows:
            entity_info = self.schema['entities'].get(entity, {})
            csv_info = entity_info.get('csv', {})
            csv_columns = csv_info.get('columns', [])
            
            staged_file = self.staging_dir / f"{entity}.csv"
            
            with open(staged_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
                writer.writeheader()
                for row in valid_rows:
                    # Ensure all columns present
                    output_row = {col: row.get(col, '') for col in csv_columns}
                    writer.writerow(output_row)
        
        return {
            'entity': entity,
            'sheet': sheet_name,
            'valid_count': len(valid_rows),
            'error_count': len(error_records),
            'staged_file': str(staged_file) if staged_file else None,
            'errors': error_records
        }
    
    def stage_all(self) -> Dict[str, Any]:
        """
        Stage all entities in dependency order with two-pass FK resolution.
        
        Pass 1: Stage entities using existing data/ CSVs for FK lookups
        Pass 2: Re-stage entities that had FK errors, now using staged/ data
        
        Returns:
            Summary dict with results per entity
        """
        results = {}
        sheets = self.mapping.get('sheets', [])
        
        # Use ingestion order from schema
        ingestion_order = self.schema.get('ingestionOrder', [])
        
        # Map entities to their sheet configs
        entity_to_config = {s.get('entity'): s for s in sheets if s.get('entity')}
        
        # === PASS 1: Stage with existing data/ only ===
        print("Pass 1: Staging with existing data/...")
        for entity in ingestion_order:
            if entity not in entity_to_config:
                continue
            
            sheet_config = entity_to_config[entity]
            result = self.stage_entity(entity, sheet_config)
            results[entity] = result
            
            print(f"✓ {entity}: {result['valid_count']} valid, {result['error_count']} errors")
        
        # === ITERATIVE PASSES: Keep re-staging entities with FK errors until no improvement ===
        max_passes = 5
        pass_num = 2
        
        while pass_num <= max_passes:
            # Find entities with FK errors
            entities_with_fk_errors = []
            for entity, result in results.items():
                if result['error_count'] > 0:
                    # Check if any errors are FK-related
                    has_fk_error = any(
                        'Could not resolve FK' in err
                        for err_rec in result['errors']
                        for err in err_rec['errors']
                    )
                    if has_fk_error:
                        entities_with_fk_errors.append(entity)
            
            if not entities_with_fk_errors:
                break  # No more FK errors
            
            print(f"\nPass {pass_num}: Re-staging {len(entities_with_fk_errors)} entities with FK errors using staged data...")
            
            # Recreate transformer with staging_dir enabled AND clear FK cache
            self.transformer = RowTransformer(
                self.schema,
                self.mapping,
                self.data_dir,
                self.staging_dir
            )
            
            # Track if we made progress
            total_errors_before = sum(results[e]['error_count'] for e in entities_with_fk_errors)
            
            for entity in entities_with_fk_errors:
                sheet_config = entity_to_config[entity]
                result = self.stage_entity(entity, sheet_config)
                results[entity] = result
                
                print(f"✓ {entity}: {result['valid_count']} valid, {result['error_count']} errors")
            
            total_errors_after = sum(results[e]['error_count'] for e in entities_with_fk_errors)
            
            # Stop if no improvement
            if total_errors_after >= total_errors_before:
                print(f"  No improvement in pass {pass_num}, stopping.")
                break
            
            pass_num += 1
        
        return results


def main():
    """CLI entry point."""
    import sys
    
    root = Path(__file__).parent.parent
    schema_path = root / 'build' / 'schema.json'
    mapping_path = root / 'config' / 'mapping_generated.yaml'
    workbook_path = root / 'Khavda Phase-3 Solar_Projects and SO Data (1).xlsx'
    data_dir = root / 'data'
    staging_dir = root / 'staging'
    
    if not schema_path.exists():
        print("ERROR: Run 'python -m src.build_schema' first", file=sys.stderr)
        sys.exit(1)
    
    if not mapping_path.exists():
        print("ERROR: Run 'python -m src.generate_mapping' first", file=sys.stderr)
        sys.exit(1)
    
    if not workbook_path.exists():
        print(f"ERROR: Workbook not found: {workbook_path}", file=sys.stderr)
        sys.exit(1)
    
    engine = StagingEngine(schema_path, mapping_path, workbook_path, data_dir, staging_dir)
    
    print("=" * 60)
    print("STAGING PIPELINE")
    print("=" * 60)
    
    results = engine.stage_all()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_valid = sum(r['valid_count'] for r in results.values())
    total_errors = sum(r['error_count'] for r in results.values())
    
    print(f"\nTotal valid rows: {total_valid}")
    print(f"Total errors: {total_errors}")
    
    if total_errors > 0:
        print("\nErrors by entity:")
        for entity, result in results.items():
            if result['error_count'] > 0:
                print(f"\n  {entity}: {result['error_count']} errors")
                for err_rec in result['errors'][:3]:  # Show first 3
                    print(f"    Row {err_rec['row_num']}: {', '.join(err_rec['errors'])}")
    
    print(f"\nStaged files written to: {staging_dir}")


if __name__ == '__main__':
    main()
