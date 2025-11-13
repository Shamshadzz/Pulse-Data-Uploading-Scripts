"""
Foreign key lookup resolver.
Resolves *_ID fields by looking up natural keys in existing CSV data.
"""
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class FKResolver:
    """Resolves foreign keys via natural key lookups."""
    
    def __init__(self, data_dir: Path, schema: Dict[str, Any], staging_dir: Optional[Path] = None):
        self.data_dir = data_dir
        self.staging_dir = staging_dir
        self.schema = schema
        self.cache: Dict[str, List[Dict[str, str]]] = {}
    
    def _load_entity_data(self, entity: str) -> List[Dict[str, str]]:
        """Load existing CSV data for an entity, checking both data and staging directories."""
        if entity in self.cache:
            return self.cache[entity]
        
        entity_info = self.schema['entities'].get(entity)
        if not entity_info:
            return []
        
        csv_info = entity_info.get('csv')
        if not csv_info:
            return []
        
        rows = []
        
        # Load from primary data directory
        csv_path = self.data_dir / f"CCTECH.DRS.ENTITIES-{entity}.csv"
        if csv_path.exists():
            try:
                with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        rows.append(row)
            except Exception as e:
                print(f"Warning: Could not load {entity} from data/: {e}")
        
        # Also load from staging directory if available (for multi-entity FK resolution)
        if self.staging_dir:
            staging_path = self.staging_dir / f"{entity}.csv"
            if staging_path.exists():
                try:
                    with open(staging_path, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            rows.append(row)
                except Exception as e:
                    print(f"Warning: Could not load {entity} from staging/: {e}")
        
        self.cache[entity] = rows
        return rows
    
    def lookup_id(
        self,
        target_entity: str,
        match_fields: List[Dict[str, str]],
        row_values: Dict[str, Any]
    ) -> Optional[str]:
        """
        Lookup ID in target entity by matching natural keys.
        
        Args:
            target_entity: Entity to look up (e.g., 'VENDORS')
            match_fields: List of {field: 'CODE', from: 'Vendor Code'} dicts
            row_values: Current Excel row values
        
        Returns:
            ID string if found, None otherwise
        """
        data = self._load_entity_data(target_entity)
        if not data:
            return None
        
        # Build match criteria from Excel values
        criteria = {}
        for mf in match_fields:
            field = mf.get('field')
            from_col = mf.get('from')
            if field and from_col and from_col in row_values:
                value = row_values[from_col]
                if value is not None and str(value).strip():
                    criteria[field] = str(value).strip()
        
        if not criteria:
            return None
        
        # Search for matching row
        for csv_row in data:
            match = True
            for field, value in criteria.items():
                csv_value = csv_row.get(field, '').strip()
                
                # Handle FK fields: might already be resolved IDs
                # For compound keys like CLUSTER_ID, we need to resolve it first
                if field.endswith('_ID') and csv_value:
                    # This is an ID field, need exact match
                    if csv_value != value:
                        match = False
                        break
                else:
                    # Natural key field, case-insensitive
                    if csv_value.upper() != value.upper():
                        match = False
                        break
            
            if match:
                return csv_row.get('ID')
        
        return None
    
    def resolve_all_fks(
        self,
        entity: str,
        lookups_config: Dict[str, Any],
        excel_row: Dict[str, Any]
    ) -> Dict[str, Optional[str]]:
        """
        Resolve all FK fields for a row.
        
        Args:
            entity: Target entity name
            lookups_config: Lookup configuration from mapping.yaml
            excel_row: Excel row values
        
        Returns:
            Dict of {FK_field: resolved_ID or None}
        """
        resolved = {}
        
        for fk_field, lookup_def in lookups_config.items():
            target_entity = lookup_def.get('entity')
            match_fields = lookup_def.get('match', [])
            
            if not target_entity:
                continue
            
            # Check if Excel row already provides the *_ID directly
            if fk_field in excel_row and excel_row[fk_field]:
                resolved[fk_field] = str(excel_row[fk_field]).strip()
                continue
            
            # Otherwise, lookup by natural key
            found_id = self.lookup_id(target_entity, match_fields, excel_row)
            resolved[fk_field] = found_id
        
        return resolved
    
    def validate_referential_integrity(
        self,
        entity: str,
        row: Dict[str, Any],
        fk_resolutions: Dict[str, Optional[str]]
    ) -> List[Tuple[str, str]]:
        """
        Validate that all FK resolutions succeeded.
        
        Returns:
            List of (field, error_message) tuples
        """
        errors = []
        entity_info = self.schema['entities'].get(entity, {})
        
        for fk_field, resolved_id in fk_resolutions.items():
            # Check if field is nullable (heuristic: not in required fields)
            # For now, we'll be lenient and only error on truly required FKs
            
            if resolved_id is None:
                # Check if this FK is critical
                # Critical = target entity exists and should be resolvable
                errors.append((fk_field, f"Could not resolve foreign key"))
        
        return errors


if __name__ == '__main__':
    import json
    from pathlib import Path
    
    root = Path(__file__).parent.parent
    schema_path = root / 'build' / 'schema.json'
    data_dir = root / 'data'
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    resolver = FKResolver(data_dir, schema)
    
    # Test: lookup a vendor by code
    test_row = {'Vendor Code': 'V001', 'Vendor Name': 'Test Vendor'}
    vendor_id = resolver.lookup_id('VENDORS', [{'field': 'CODE', 'from': 'Vendor Code'}], test_row)
    print(f"Test lookup VENDORS by CODE: {vendor_id}")
