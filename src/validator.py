"""
Data validator: validates enums, uniqueness, referential integrity, XOR rules.
"""
from typing import Dict, List, Any, Tuple, Set, Optional
from datetime import datetime
import re


class DataValidator:
    """Validates data against schema rules."""
    
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.enums = schema.get('enums', {})
        self.entities = schema.get('entities', {})
    
    def validate_enum(self, field_name: str, value: Any, enum_type: str) -> Optional[str]:
        """
        Validate enum value.
        
        Returns:
            Error message if invalid, None if valid
        """
        if value is None or str(value).strip() == '':
            return None  # Nullable
        
        str_value = str(value).strip()
        allowed = self.enums.get(enum_type, [])
        
        if str_value not in allowed:
            return f"Invalid enum value '{str_value}' for {field_name}. Allowed: {', '.join(allowed)}"
        
        return None
    
    def validate_type(self, field_name: str, value: Any, field_type: str) -> Tuple[Any, Optional[str]]:
        """
        Coerce and validate field type.
        
        Returns:
            (coerced_value, error_message)
        """
        if value is None or str(value).strip() == '':
            return None, None
        
        type_upper = field_type.upper()
        
        try:
            # UUID
            if type_upper.startswith('UUID'):
                str_val = str(value).strip()
                # Basic UUID format check
                if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', str_val, re.I):
                    return str_val, None
                return str_val, f"Invalid UUID format for {field_name}"
            
            # String types
            if 'STRING' in type_upper or 'LARGESTRING' in type_upper:
                return str(value).strip(), None
            
            # Integer types
            if type_upper in ['INTEGER', 'INTEGER64']:
                if isinstance(value, (int, float)):
                    return int(value), None
                return int(str(value).strip()), None
            
            # Decimal/Float
            if 'DECIMAL' in type_upper or 'FLOAT' in type_upper:
                if isinstance(value, (int, float)):
                    return float(value), None
                return float(str(value).strip()), None
            
            # Boolean
            if 'BOOLEAN' in type_upper:
                if isinstance(value, bool):
                    return value, None
                str_val = str(value).strip().lower()
                if str_val in ['true', '1', 'yes', 't', 'y']:
                    return True, None
                if str_val in ['false', '0', 'no', 'f', 'n', '']:
                    return False, None
                return None, f"Invalid boolean value '{value}' for {field_name}"
            
            # Timestamp
            if 'TIMESTAMP' in type_upper:
                if isinstance(value, datetime):
                    return value.isoformat(), None
                str_val = str(value).strip()
                # Try ISO format
                try:
                    dt = datetime.fromisoformat(str_val)
                    return dt.isoformat(), None
                except:
                    pass
                # Try common formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                    try:
                        dt = datetime.strptime(str_val, fmt)
                        return dt.isoformat(), None
                    except:
                        pass
                return str_val, f"Cannot parse timestamp '{value}' for {field_name}"
            
            # Default: string
            return str(value).strip(), None
        
        except (ValueError, TypeError) as e:
            return None, f"Type coercion failed for {field_name}: {e}"
    
    def validate_unique_constraints(
        self,
        entity: str,
        row: Dict[str, Any],
        existing_rows: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Check unique constraints against existing data.
        
        Returns:
            List of error messages
        """
        errors = []
        entity_info = self.entities.get(entity, {})
        constraints = entity_info.get('uniqueConstraints', [])
        
        for constraint in constraints:
            columns = constraint.get('columns', [])
            name = constraint.get('name', 'unique')
            
            # Build key from current row
            key_values = []
            missing = False
            for col in columns:
                val = row.get(col)
                if val is None or str(val).strip() == '':
                    missing = True
                    break
                key_values.append(str(val).strip().upper())
            
            if missing:
                continue  # Can't check if key is incomplete
            
            key_tuple = tuple(key_values)
            
            # Check against existing rows
            for existing in existing_rows:
                existing_key = []
                for col in columns:
                    val = existing.get(col)
                    if val is None or str(val).strip() == '':
                        break
                    existing_key.append(str(val).strip().upper())
                
                if len(existing_key) == len(key_values) and tuple(existing_key) == key_tuple:
                    col_str = ', '.join(f"{c}={row.get(c)}" for c in columns)
                    errors.append(f"Unique constraint '{name}' violated: {col_str}")
                    break
        
        return errors
    
    def validate_xor_rule(self, entity: str, row: Dict[str, Any]) -> Optional[str]:
        """
        Validate XOR rules (e.g., UNITSCOPE must have exactly one of RFI_ID or NC_ID).
        
        Returns:
            Error message if violated, None if valid
        """
        # Hard-coded XOR rules from schema
        if entity == 'UNITSCOPE':
            rfi_id = row.get('RFI_ID')
            nc_id = row.get('NC_ID')
            
            has_rfi = rfi_id is not None and str(rfi_id).strip() != ''
            has_nc = nc_id is not None and str(nc_id).strip() != ''
            
            if has_rfi and has_nc:
                return "XOR violation: UNITSCOPE must have RFI_ID OR NC_ID, not both"
            if not has_rfi and not has_nc:
                return "XOR violation: UNITSCOPE must have either RFI_ID or NC_ID"
        
        return None
    
    def validate_required_fields(self, entity: str, row: Dict[str, Any]) -> List[str]:
        """
        Check required fields (heuristic: key fields and some critical FKs).
        
        Returns:
            List of error messages
        """
        errors = []
        entity_info = self.entities.get(entity, {})
        
        # Check key field
        for field in entity_info.get('fields', []):
            if field.get('key'):
                fname = field['name']
                val = row.get(fname)
                if val is None or str(val).strip() == '':
                    errors.append(f"Required key field '{fname}' is missing")
        
        return errors
