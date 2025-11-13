"""
Row transformer: applies columnMap, generates UUIDs, resolves FKs, validates.
"""
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
import csv

from src.validator import DataValidator
from src.fk_resolver import FKResolver
from src.dedup_config import should_deduplicate, get_dedup_keys
from src.policy import get_duplicate_policy


class RowTransformer:
    """Transforms Excel rows to CSV-ready format."""
    
    def __init__(
        self,
        schema: Dict[str, Any],
        mapping_config: Dict[str, Any],
        data_dir: Path,
        staging_dir: Optional[Path] = None
    ):
        self.schema = schema
        self.mapping_config = mapping_config
        self.data_dir = data_dir
        self.staging_dir = staging_dir
        self.validator = DataValidator(schema)
        self.fk_resolver = FKResolver(data_dir, schema, staging_dir)
    
    def _generate_uuid(self) -> str:
        """Generate a new UUIDv4."""
        return str(uuid.uuid4())
    
    def _load_existing_csv(self, csv_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Load existing CSV to check uniqueness and get headers.
        
        Returns:
            (headers, rows)
        """
        if not csv_path.exists():
            return [], []
        
        headers = []
        rows = []
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for row in reader:
                    rows.append(row)
        except Exception as e:
            print(f"Warning: Could not load {csv_path}: {e}")
        
        return headers, rows
    
    def transform_row(
        self,
        entity: str,
        sheet_config: Dict[str, Any],
        excel_row: Dict[str, Any],
        existing_rows: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Transform a single Excel row to CSV format.
        
        Args:
            entity: Target entity name
            sheet_config: Sheet configuration from mapping.yaml
            excel_row: Raw Excel row data
            existing_rows: Existing CSV rows for uniqueness check
        
        Returns:
            (transformed_row, errors)
            transformed_row is None if validation fails
        """
        errors = []
        entity_info = self.schema['entities'].get(entity, {})
        csv_info = entity_info.get('csv', {})
        csv_columns = csv_info.get('columns', [])
        
        # Initialize output row with all CSV columns
        output = {col: None for col in csv_columns}
        
        # Apply columnMap
        column_map = sheet_config.get('columnMap', {})
        for excel_col, csv_col in column_map.items():
            if excel_col in excel_row:
                value = excel_row[excel_col]
                output[csv_col] = value
        
        # Apply defaults
        defaults = sheet_config.get('defaults', {})
        for csv_col, default_val in defaults.items():
            if csv_col in output and (output[csv_col] is None or str(output[csv_col]).strip() == ''):
                output[csv_col] = default_val
        
        # Handle ID field
        id_config = sheet_config.get('id', {})
        id_column = id_config.get('column', 'ID')
        uuid_policy = id_config.get('uuidPolicy', 'preserve')
        
        if id_column in output:
            current_id = output[id_column]
            if uuid_policy == 'generate_if_blank':
                if current_id is None or str(current_id).strip() == '':
                    output[id_column] = self._generate_uuid()
        
        # Resolve FKs
        lookups_config = sheet_config.get('lookups', {})
        if lookups_config:
            # Build enhanced row for FK resolution (includes already mapped values)
            enhanced_row = {**excel_row, **output}
            fk_resolutions = self.fk_resolver.resolve_all_fks(entity, lookups_config, enhanced_row)
            
            for fk_field, resolved_id in fk_resolutions.items():
                if resolved_id:
                    output[fk_field] = resolved_id
                else:
                    # Check if FK is optional
                    fk_config = lookups_config.get(fk_field, {})
                    is_optional = fk_config.get('optional', False)
                    
                    if not is_optional:
                        # Required FK is missing
                        if fk_field in output and (output[fk_field] is None or str(output[fk_field]).strip() == ''):
                            errors.append(f"Could not resolve FK '{fk_field}'")
        
        # Type coercion and validation
        for field in entity_info.get('fields', []):
            fname = field['name']
            ftype = field.get('type', 'String')
            
            if fname not in output:
                continue
            
            value = output[fname]
            
            # Type coercion
            coerced, type_err = self.validator.validate_type(fname, value, ftype)
            if type_err:
                errors.append(type_err)
            else:
                output[fname] = coerced
            
            # Enum validation
            if ftype in self.schema.get('enums', {}):
                enum_err = self.validator.validate_enum(fname, coerced, ftype)
                if enum_err:
                    errors.append(enum_err)
        
        # Uniqueness validation
        unique_errors = self.validator.validate_unique_constraints(entity, output, existing_rows)
        errors.extend(unique_errors)
        
        # XOR validation
        xor_err = self.validator.validate_xor_rule(entity, output)
        if xor_err:
            errors.append(xor_err)
        
        # Required fields
        required_errors = self.validator.validate_required_fields(entity, output)
        errors.extend(required_errors)
        
        if errors:
            return None, errors
        
        return output, []
    
    def transform_entity(
        self,
        entity: str,
        sheet_config: Dict[str, Any],
        excel_rows: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Transform all Excel rows for an entity.
        
        Returns:
            (valid_rows, error_records)
            error_records: list of {row_num, excel_row, errors}
        """
        entity_info = self.schema['entities'].get(entity, {})
        csv_info = entity_info.get('csv', {})
        csv_path = Path(csv_info['file']) if csv_info.get('file') else None
        
        if not csv_path:
            return [], []
        
        # Load existing data
        headers, existing_rows = self._load_existing_csv(csv_path)
        
        valid_rows = []
        error_records = []
        
        # Track rows in this batch for intra-batch uniqueness
        all_rows = existing_rows.copy()

        # Build existing key set for master entities to skip-if-exists (case-insensitive)
        existing_key_set: Set[tuple] = set()
        if should_deduplicate(entity):
            dedup_keys = get_dedup_keys(entity)
            for er in existing_rows:
                key = tuple((str(er.get(k, '')).strip().upper()) for k in dedup_keys)
                existing_key_set.add(key)

        # Deduplication tracking for master data within this batch
        seen_keys: Set[tuple] = set()
        
        for idx, excel_row in enumerate(excel_rows, start=1):
            # Check if this entity should be deduplicated
            if should_deduplicate(entity):
                dedup_keys = get_dedup_keys(entity)
                
                # Build key tuple from Excel row
                key_values = []
                for key_field in dedup_keys:
                    # Try to get the Excel column that maps to this CSV field
                    excel_col = None
                    for excel_key, csv_field in sheet_config.get('columnMap', {}).items():
                        if csv_field == key_field:
                            excel_col = excel_key
                            break
                    
                    if excel_col and excel_col in excel_row:
                        val = str(excel_row[excel_col] or '').strip()
                        key_values.append(val.lower())  # Case-insensitive
                    else:
                        key_values.append('')
                
                key_tuple = tuple(key_values)
                
                # Skip rows with empty/blank dedup keys (invalid master data)
                if all(not v for v in key_values):
                    continue  # Skip silently - empty key fields
                
                # Skip if we've already seen this key in this batch
                # For master data, silently skip duplicates (they're expected in transactional Excel)
                if key_tuple in seen_keys:
                    continue  # Skip silently - no error
                
                seen_keys.add(key_tuple)
            
            transformed, errors = self.transform_row(entity, sheet_config, excel_row, all_rows)
            
            if transformed:
                # After transform: for master data, skip if this key already exists in CSV (do not restage)
                if should_deduplicate(entity):
                    dedup_keys = get_dedup_keys(entity)
                    key_tuple = tuple((str(transformed.get(k, '')).strip().upper()) for k in dedup_keys)
                    if key_tuple in existing_key_set:
                        # Already present in original CSV → skip staging to avoid duplicates
                        continue
                    # Track so subsequent transformed rows are also deduped
                    existing_key_set.add(key_tuple)

                valid_rows.append(transformed)
                all_rows.append(transformed)
            else:
                # For master data entities, check if the error is "already exists"
                # If so, treat as INFO (not ERROR) since we're just reusing existing record
                if should_deduplicate(entity) and any('Unique constraint' in err and 'violated' in err for err in errors):
                    # This is a duplicate of existing data - skip silently for master data
                    # (FK resolution will find the existing record)
                    continue
                
                # Duplicates policy: if all errors are unique-constraint violations and policy is 'skip', skip row
                policy = get_duplicate_policy(entity)
                if policy == 'skip':
                    only_unique_errors = all('Unique constraint' in e for e in errors)
                    if only_unique_errors:
                        # Skip silently; record as info in error records for traceability
                        error_records.append({
                            'row_num': idx,
                            'excel_row': excel_row,
                            'errors': ["Skipped due to duplicate (unique constraint)"]
                        })
                        continue

                error_records.append({
                    'row_num': idx,
                    'excel_row': excel_row,
                    'errors': errors
                })
        
        return valid_rows, error_records
