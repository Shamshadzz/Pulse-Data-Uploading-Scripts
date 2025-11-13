"""
Append-only CSV writer: safely appends staged rows to existing CSVs.
"""
import csv
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class AppendOnlyWriter:
    """Safely appends validated rows to CSVs without modifying headers or existing data."""
    
    def __init__(self, data_dir: Path, staging_dir: Path, backup_dir: Path):
        self.data_dir = data_dir
        self.staging_dir = staging_dir
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(exist_ok=True, parents=True)
    
    def _backup_csv(self, csv_path: Path) -> Path:
        """Create timestamped backup of CSV file."""
        if not csv_path.exists():
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{csv_path.stem}_{timestamp}.bak.csv"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(csv_path, backup_path)
        return backup_path
    
    def _get_headers(self, csv_path: Path, staged_path: Path) -> Dict[str, List[str]]:
        """Return headers for existing CSV (if any) and staged CSV.
        Always prefer writing using existing headers order; for missing values, write blanks.
        """
        existing_headers: List[str] = []
        if csv_path.exists():
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                try:
                    existing_headers = next(reader)
                except StopIteration:
                    existing_headers = []
        
        with open(staged_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                staged_headers = next(reader)
            except StopIteration:
                staged_headers = []
        
        return { 'existing': existing_headers, 'staged': staged_headers }
    
    def append_entity(self, entity: str, csv_file: str, staged_file: Path) -> Dict[str, Any]:
        """
        Append staged rows to existing CSV.
        
        Returns:
            {
                'entity': str,
                'appended': int,
                'backup': str or None,
                'error': str or None
            }
        """
        csv_path = Path(csv_file)
        
        if not staged_file.exists():
            return {
                'entity': entity,
                'appended': 0,
                'backup': None,
                'error': 'Staged file not found'
            }
        
        # Resolve headers (support extra/missing columns by filling blanks for missing)
        headers = self._get_headers(csv_path, staged_file)
        existing_headers = headers['existing']
        staged_headers = headers['staged']
        
        # Backup existing file
        backup_path = None
        if csv_path.exists():
            backup_path = self._backup_csv(csv_path)
        
        # Count rows to append
        with open(staged_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            rows_to_append = sum(1 for _ in reader)
        
        # Append staged rows to existing CSV
        try:
            if csv_path.exists():
                # Append mode using existing headers; fill missing with blanks
                with open(csv_path, 'a', newline='', encoding='utf-8') as dest:
                    writer = csv.DictWriter(dest, fieldnames=existing_headers, extrasaction='ignore')
                    with open(staged_file, 'r', newline='', encoding='utf-8') as src:
                        dict_reader = csv.DictReader(src)
                        for row in dict_reader:
                            out_row = {h: row.get(h, '') for h in existing_headers}
                            writer.writerow(out_row)
            else:
                # New file: write staged as-is with header
                with open(csv_path, 'w', newline='', encoding='utf-8') as dest:
                    writer = csv.DictWriter(dest, fieldnames=staged_headers, extrasaction='ignore')
                    writer.writeheader()
                    with open(staged_file, 'r', newline='', encoding='utf-8') as src:
                        dict_reader = csv.DictReader(src)
                        for row in dict_reader:
                            # Ensure any missing staged header values default to ''
                            out_row = {h: row.get(h, '') for h in staged_headers}
                            writer.writerow(out_row)
            
            return {
                'entity': entity,
                'appended': rows_to_append,
                'backup': str(backup_path) if backup_path else None,
                'error': None
            }
        
        except Exception as e:
            # Restore backup on error
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, csv_path)
            
            return {
                'entity': entity,
                'appended': 0,
                'backup': str(backup_path) if backup_path else None,
                'error': f'Failed to append: {e}'
            }
    
    def append_all(self, staging_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append all staged entities to their CSVs.
        
        Args:
            staging_results: Output from StagingEngine.stage_all()
        
        Returns:
            Summary dict with append results per entity
        """
        results = {}
        
        for entity, stage_result in staging_results.items():
            staged_file = stage_result.get('staged_file')
            
            if not staged_file or stage_result['valid_count'] == 0:
                results[entity] = {
                    'entity': entity,
                    'appended': 0,
                    'backup': None,
                    'error': 'No valid rows to append'
                }
                continue
            
            # Get CSV file path from stage result
            csv_file = None
            # Reconstruct from entity name
            csv_file = self.data_dir / f"CCTECH.DRS.ENTITIES-{entity}.csv"
            
            result = self.append_entity(entity, str(csv_file), Path(staged_file))
            results[entity] = result
            
            if result['error']:
                print(f"✗ {entity}: {result['error']}")
            else:
                print(f"✓ {entity}: appended {result['appended']} rows")
        
        return results


def main():
    """CLI entry point for append operation."""
    import sys
    import json
    
    root = Path(__file__).parent.parent
    data_dir = root / 'data'
    staging_dir = root / 'staging'
    backup_dir = root / 'backups'
    
    if not staging_dir.exists():
        print("ERROR: Run 'python -m src.staging_engine' first", file=sys.stderr)
        sys.exit(1)
    
    # Load staging results
    staging_files = list(staging_dir.glob('*.csv'))
    if not staging_files:
        print("ERROR: No staged files found", file=sys.stderr)
        sys.exit(1)
    
    # Build staging results dict
    staging_results = {}
    for staged_file in staging_files:
        entity = staged_file.stem
        staging_results[entity] = {
            'entity': entity,
            'valid_count': 1,  # Placeholder
            'staged_file': str(staged_file)
        }
    
    print("=" * 60)
    print("APPEND-ONLY WRITER")
    print("=" * 60)
    print(f"\nBacking up CSVs to: {backup_dir}\n")
    
    writer = AppendOnlyWriter(data_dir, staging_dir, backup_dir)
    results = writer.append_all(staging_results)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_appended = sum(r['appended'] for r in results.values())
    total_errors = sum(1 for r in results.values() if r['error'])
    
    print(f"\nTotal rows appended: {total_appended}")
    print(f"Entities with errors: {total_errors}")
    
    if total_errors > 0:
        print("\nErrors:")
        for entity, result in results.items():
            if result['error']:
                print(f"  {entity}: {result['error']}")


if __name__ == '__main__':
    main()
