# Pulse Data Uploading Scripts - ETL Pipeline Documentation

Enterprise-grade ETL pipeline for importing Excel data (3-row hierarchical headers) into CDS-backed CSV files with validation, FK resolution, deduplication, and append-only operations.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
- [Excel Format](#excel-format)
- [CLI Commands](#cli-commands)
- [Key Features](#key-features)
- [Validation Rules](#validation-rules)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

This ETL pipeline automates the process of importing data from Excel workbooks into existing CSV files while:

- ✅ Preserving existing data and headers
- ✅ Validating data types, enums, and unique constraints
- ✅ Resolving foreign keys by natural keys (case-insensitive)
- ✅ Deduplicating master data entities
- ✅ Generating UUIDs for primary keys
- ✅ Supporting optional foreign keys
- ✅ Creating automatic backups

**Use Case**: Import 255 Excel rows → generate 347 CSV rows across 7 entities with proper FK relationships.

---

## Architecture

### Data Flow

```
Excel (3-row headers)
  → Schema Parser (CDS)
  → Mapping Configuration
  → Staging Engine (multi-pass FK resolution)
  → Validation & Transformation
  → Append-only Commit
  → CSV Files (data/)
```

### Key Principles

1. **Append-Only**: Never modify existing CSV data or headers
2. **Schema-Driven**: CDS schema defines entities, constraints, dependencies
3. **Multi-Pass Staging**: Iteratively resolve cascading FKs
4. **Smart Deduplication**: Master data staged once, transactional data always staged
5. **Natural Key Matching**: FK resolution via business keys (CODE, NAME)

---

## Directory Structure

```
Pulse-Data-Uploading-Scripts/
├── schema.cds                 # SAP CDS-like schema definition
├── data/                      # Target CSV files (existing data)
│   └── CCTECH.DRS.ENTITIES-*.csv
├── staging/                   # Temporary staging files
│   └── *.csv
├── backups/                   # Automatic backups (timestamped)
│   └── YYYY-MM-DD_HHMMSS/
├── build/
│   └── schema.json           # Compiled schema with dependencies
├── config/
│   ├── mapping.yaml          # Manual mapping configuration
│   └── mapping_generated.yaml # Auto-generated mapping skeleton
├── src/
│   ├── main.py               # CLI entry point
│   ├── cds_parser.py         # Parse CDS schema
│   ├── csv_introspect.py     # Analyze CSV headers
│   ├── build_schema.py       # Compile schema with ingestion order
│   ├── generate_mapping.py   # Auto-generate mapping from Excel
│   ├── introspect_excel.py   # Analyze Excel structure
│   ├── staging_engine.py     # Multi-pass staging orchestrator
│   ├── transformer.py        # Row transformation & deduplication
│   ├── validator.py          # Data validation (types, enums, constraints)
│   ├── fk_resolver.py        # Foreign key lookup by natural keys
│   ├── append_writer.py      # Append-only CSV writer with backups
│   ├── dedup_config.py       # Deduplication rules per entity
│   └── policy.py             # Duplicate handling policies
└── append_remaining.py       # Utility for manual append operations
```

---

## Core Components

### 1. Schema Parser (`src/cds_parser.py`)

**Purpose**: Parse SAP CDS-like schema into structured JSON

**Key Functions**:

- `parse_cds(content)` - Extract entities, fields, associations, enums, unique constraints
- `build_dependencies(parsed)` - Build entity dependency graph
- `topo_sort(deps)` - Topological sort for safe ingestion order

**Input**: `schema.cds` with CDS syntax
**Output**: Structured entity definitions with field types, constraints, associations

**Example**:

```cds
@assert.unique: {unique_vendor: [CODE]}
entity VENDORS {
  key ID:   UUID;
      CODE: String;
      NAME: String;
}
```

### 2. Schema Builder (`src/build_schema.py`)

**Purpose**: Compile schema with CSV metadata and ingestion order

**Process**:

1. Parse CDS schema → entities, enums, associations
2. Introspect existing CSV headers in `data/`
3. Match CDS fields to CSV columns
4. Build dependency graph (who references whom)
5. Topologically sort for safe ingestion order

**Output**: `build/schema.json`

```json
{
  "entities": {
    "VENDORS": {
      "fields": { "ID": "UUID", "CODE": "String" },
      "unique": [["CODE"]],
      "csvFile": "data/CCTECH.DRS.ENTITIES-VENDORS.csv"
    }
  },
  "dependencies": { "PROJECTS": ["SPVS"] },
  "ingestionOrder": ["SPVS", "PROJECTS", "SERVICEORDERS"]
}
```

**Usage**:

```cmd
python -m src.build_schema
```

### 3. Mapping Generator (`src/generate_mapping.py`)

**Purpose**: Auto-generate Excel-to-CSV column mappings

**Features**:

- Reads 3-row hierarchical Excel headers
- Merges multi-row header cells (openpyxl)
- Generates YAML skeleton with columnMap and lookup stubs
- Detects ID columns and FK candidates

**Output**: `config/mapping_generated.yaml`

```yaml
sheets:
  - sheet: "Khavda-PhIII-Solar-SO Mapping"
    entity: SERVICEORDERS
    columnMap:
      "Project": NAME
      "Vendor Code": CODE
    lookups:
      VENDOR_ID:
        entity: VENDORS
        match:
          - field: CODE
            from: "Vendor Code"
```

**Usage**:

```cmd
python -m src.generate_mapping
```

### 4. Staging Engine (`src/staging_engine.py`)

**Purpose**: Orchestrate multi-pass staging with iterative FK resolution

**Algorithm**:

```
Pass 1: Stage with FK lookups from data/ only
  → Resolve FKs for rows with existing references

Pass 2-5: Re-stage entities with FK errors
  → Resolve FKs from data/ + staging/
  → Loop until no improvement (or max 5 passes)

Result: staging/*.csv files (validated, deduplicated)
```

**Key Features**:

- **Iterative FK Resolution**: Cascading dependencies resolved across passes
- **Ingestion Order**: Stages entities in topological order
- **Error Tracking**: Per-entity error counts
- **Case-Insensitive Lookups**: "Khavda" matches "KHAVDA"
- **Deduplication**: Skip duplicate master data

**Usage**:

```cmd
python -m src.main stage
```

**Output Example**:

```
Pass 1: Staging entities...
  ✓ SPVS: 7 valid, 0 errors
  ✓ PROJECTS: 10 valid, 0 errors
  ✗ SERVICEORDERS: 100 valid, 155 errors (FK failures)

Pass 2: Re-staging 1 entities with errors...
  ✓ SERVICEORDERS: 254 valid, 1 error

Pass 3: No improvement. Stopping.

Summary: 347 valid rows, 1 error
```

### 5. Row Transformer (`src/transformer.py`)

**Purpose**: Transform, validate, and deduplicate Excel rows

**Transformation Pipeline**:

1. **Column Mapping**: Apply `columnMap` from Excel → CSV fields
2. **Defaults**: Fill default values for empty fields
3. **UUID Generation**: Generate primary keys based on `uuidPolicy`
4. **FK Resolution**: Lookup foreign key IDs by natural keys
5. **Type Coercion**: Convert strings to typed values
6. **Enum Validation**: Check against allowed values
7. **Unique Constraints**: Validate multi-column uniqueness
8. **Deduplication**: Skip intra-batch and existing duplicates
9. **Skip-if-Exists**: Skip rows already in original CSV

**Deduplication Logic**:

- **Intra-batch**: Skip duplicate natural keys within Excel rows
- **Skip-if-exists**: Skip if natural key already in `data/` CSV
- **Empty key filter**: Skip rows with all-blank dedup keys

**Example**:

```python
# Excel has "KHAVDA" repeated 255 times
# Only first occurrence is staged → reuse ID for all
```

**Optional FK Support**:

```yaml
VENDOR_ID:
  optional: true # Can be null
```

- Missing vendor code → stage row with blank VENDOR_ID ✓
- Present vendor code → resolve and fill VENDOR_ID ✓

### 6. FK Resolver (`src/fk_resolver.py`)

**Purpose**: Resolve foreign key IDs by natural keys

**Features**:

- **Dual-source lookup**: Reads both `data/` and `staging/` CSVs
- **Cache mechanism**: Loads entity data once per pass (performance)
- **Case-insensitive matching**: "ABC" = "abc" = "Abc"
- **Natural key matching**: Lookup by business keys (NAME, CODE)
- **Optional FK handling**: Returns None for missing optional FKs

**Example Lookup**:

```yaml
PROJECT_ID:
  entity: PROJECTS
  match:
    - field: NAME # Match on PROJECTS.NAME
      from: "Project" # Excel column with project name
```

**Process**:

1. Read Excel: `Project = "AGEL KHAVDA Ph3 Solar"`
2. Load PROJECTS.csv from `data/` and `staging/`
3. Search for `NAME = "AGEL KHAVDA Ph3 Solar"` (case-insensitive)
4. Return matching `ID` value
5. Cache result for subsequent lookups

**Usage in Transformer**:

```python
project_id = fk_resolver.resolve('PROJECTS', {'NAME': 'AGEL KHAVDA Ph3 Solar'})
# → 'abc-123-def-456'
```

### 7. Validator (`src/validator.py`)

**Purpose**: Validate data types, enums, and constraints

**Validations**:

**Type Coercion**:

- `UUID`: Validates format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- `String`: UTF-8 text
- `Integer`: Converts float to int (e.g., `5.0` → `5`)
- `Decimal`: Accepts int or float
- `Boolean`: `true/false/1/0/yes/no/t/f/y/n` (case-insensitive)
- `Timestamp`: ISO 8601 or common date formats

**Enum Validation**:

```cds
entity PROJECTS {
  TYPE: String enum { solar; wind; hybrid };
}
```

Rejects: `TYPE = "nuclear"` ✗

**Unique Constraints**:

```cds
@assert.unique: {unique_vendor: [CODE]}
```

- Case-insensitive: `ABC` = `abc` = `Abc`
- Multi-column: `[NAME, TYPE, CATEGORY]`

**XOR Rules** (UNITSCOPE):

```cds
// Must have RFI_ID OR NC_ID, not both or neither
entity UNITSCOPE {
  RFI_ID: UUID;
  NC_ID:  UUID;
}
```

### 8. Append Writer (`src/append_writer.py`)

**Purpose**: Append staged rows to CSV files with backups and header alignment

**Features**:

- **Atomic Backups**: Copy original files before modification
- **Header Alignment**: Match existing CSV column order exactly
- **Fill Missing Columns**: Empty string for absent fields in staged data
- **Ignore Extra Columns**: Drop staged columns not in original CSV
- **New File Creation**: Write headers if CSV doesn't exist
- **DictWriter**: Prevents UUID concatenation issues

**Safety Guarantees**:

- Backups saved to `backups/YYYY-MM-DD_HHMMSS/`
- All-or-nothing atomic commit (strict mode)
- Partial commit option (append only clean entities)

**Example**:

```python
# Existing CSV columns: [ID, NAME, CODE]
# Staged columns:       [ID, NAME, CODE, TYPE, EXTRA]
# Append result:        Fill TYPE with "", ignore EXTRA
```

### 9. Deduplication Config (`src/dedup_config.py`)

**Purpose**: Define which entities should be deduplicated and by which keys

**Master Data** (deduplicated - stage once):

```python
DEDUP_ENTITIES = {
    'CLUSTERS': ['NAME'],
    'SPVS': ['NAME'],
    'PROJECTS': ['NAME', 'TYPE', 'CATEGORY'],
    'LOCATIONS': ['NAME'],
    'PLOTS': ['NAME'],
    'VENDORS': ['CODE'],
    'PROJECTDEFINITIONS': ['CODE'],
    'PACKAGES': ['NAME'],
}
```

**Transactional Data** (never deduplicated - stage all):

```python
TRANSACTIONAL_ENTITIES = {
    'SERVICEORDERS',
}
```

**Why?**

- Master data: One entity per natural key (e.g., one KHAVDA location)
- Transactional data: Every row is unique (e.g., 255 service orders)

### 10. Duplicate Policy (`src/policy.py`)

**Purpose**: Define how to handle unique constraint violations

**Policies**:

- `'skip'`: Silently skip duplicates (log as info, not error)
- `'error'`: Fail the batch (default behavior)

**Configuration**:

```python
_ENTITY_POLICIES = {
    'SERVICEORDERS': 'skip',  # Skip duplicate SO_NUMBER conflicts
}
```

**Impact**:

- `'skip'`: Allows partial commit to append clean rows
- `'error'`: Aborts entire entity if any duplicate found

---

## Excel Format

### Header Structure (3 rows)

```
Row 1: Category headers (merged cells spanning columns)
Row 2: Sub-category headers (merged or individual)
Row 3: Actual column names (used in mapping)
Row 4+: Data rows
```

**Example**:

```
| Sr. No. | Cluster | Location | Project                | ... | Service Orders |          |
|         |         |          |                        |     | SO Number      | Vendor   |
| 1       | KHAVDA  | Kachchh  | AGEL KHAVDA Ph3 Solar  |     | 4810023149     | ABC Corp |
| 2       | KHAVDA  | Kachchh  | AGEL KHAVDA Ph3 Solar  |     | 4810023150     | XYZ Ltd  |
```

### Hierarchical Header Merging

- Row 1 "Service Orders" spans columns E-F
- Row 2 sub-categories: "SO Number", "Vendor"
- Row 3 actual names: "SO Number", "Vendor Code"

**Merged Result**: `"Service Orders > SO Number"`

### Column Mapping

```yaml
columnMap:
  "Project": NAME # Row 3 header → CSV field
  "Vendor Code": CODE
  "MMS Type": MMS_TYPE
  "Capacity\n(MWac)": CAPACITY # Handles line breaks in headers
```

### FK Lookups

```yaml
lookups:
  PROJECT_ID:
    entity: PROJECTS
    match:
      - field: NAME
        from: "Project" # Excel column with project name
```

---

## CLI Commands

### 1. Build Schema

```cmd
python -m src.build_schema
```

- Parses `schema.cds`
- Introspects CSV headers in `data/`
- Generates `build/schema.json` with:
  - Entities, fields, types
  - Unique constraints
  - Dependencies graph
  - Ingestion order

### 2. Generate Mapping

```cmd
python -m src.generate_mapping
```

- Reads Excel structure (3-row headers)
- Generates `config/mapping_generated.yaml` skeleton
- Auto-detects columnMap and lookup candidates
- Requires manual completion

### 3. Stage (Dry-Run)

```cmd
python -m src.main stage
```

- **Does NOT modify `data/` files**
- Validates all Excel data
- Resolves FKs (multi-pass)
- Writes to `staging/*.csv`
- Shows detailed error report

**Output**:

```
✓ PLOTS: 9 valid, 0 errors
✓ VENDORS: 59 valid, 0 errors
✗ SERVICEORDERS: 254 valid, 1 error

Total: 347 valid rows, 1 error
```

### 4. Commit (Strict Atomic)

```cmd
python -m src.main commit
```

- Validates all data
- **Aborts if ANY errors found**
- Creates backups in `backups/`
- Appends ALL entities atomically
- All-or-nothing guarantee

**Use When**: You have 100% clean data

### 5. Commit Partial

```cmd
python -m src.main commit-partial
```

- Validates all data
- **Appends only error-free entities**
- Skips entities with errors
- Creates backups
- Interactive confirmation

**Use When**: Some entities have errors but others are clean

**Example**:

```
✅ PLOTS: 9 rows
✅ VENDORS: 59 rows
⚠️  SERVICEORDERS: Skipped (1 error)

Append clean entities? [y/N]: y
✓ Successfully appended 68 rows
```

---

## Key Features

### 1. Iterative FK Resolution

**Problem**: Circular/cascading dependencies between entities

**Solution**: Multi-pass staging

- **Pass 1**: Resolve FKs from existing `data/` CSVs only
- **Pass 2+**: Resolve FKs from `data/` + `staging/` CSVs
- Loop until convergence (max 5 passes)

**Example Scenario**:

```
Pass 1:
  PROJECTS needs SPV_ID
    → Found in data/SPVS.csv ✓
  SOLARPROJECTATTRIBUTES needs PROJECT_ID
    → Not in data/PROJECTS.csv (new project) ✗

Pass 2:
  SOLARPROJECTATTRIBUTES needs PROJECT_ID
    → Found in staging/PROJECTS.csv ✓
  SERVICEORDERS needs PROJECT_ID + VENDOR_ID
    → Found in staging/PROJECTS.csv + data/VENDORS.csv ✓

Result: All FKs resolved in 2 passes
```

### 2. Smart Deduplication

**Master Data**: One instance per natural key

```python
# Excel repeats "KHAVDA" location 255 times
# Staging: Only first occurrence staged
# Result: 1 KHAVDA row in staging, ID reused for all references
```

**Transactional Data**: Every row is unique

```python
# 255 service orders with different SO_NUMBERs
# Staging: All 255 rows staged
```

### 3. Case-Insensitive Matching

```
Excel value:   "Khavda"
CSV value:     "KHAVDA"
Match result:  ✓ (same entity)
```

**Applied To**:

- FK natural key lookups
- Unique constraint checks
- Deduplication comparisons

### 4. Optional Foreign Keys

**Configuration**:

```yaml
VENDOR_ID:
  entity: VENDORS
  optional: true # Can be null
  match:
    - field: CODE
      from: "Vendor Code"
```

**Behavior**:

- Excel "Vendor Code" = blank → VENDOR_ID = "" ✓
- Excel "Vendor Code" = "ABC123" → lookup and fill VENDOR_ID ✓

**Use Case**: 153 service orders have no vendor codes

### 5. Skip-if-Exists

**Prevents duplicate staging of master data**:

```
Existing data/LOCATIONS.csv: KHAVDA (ID: abc-123)

Excel processing:
  Row 1: Location = "Khavda" → Skip (already exists in CSV)
  Row 2: Location = "Khavda" → Skip (intra-batch duplicate)
  Row 3: Location = "AHEJ"   → Stage (new)

Result: Only AHEJ staged, KHAVDA ID reused
```

### 6. Empty Key Filtering

**Prevents invalid master data entries**:

```python
# Excel row with blank Package name
Excel: Package = ""  (empty)

# Dedup config: PACKAGES dedup key = ['NAME']
# Result: Skip row (empty key field)
# Log: "Skipped row with empty dedup key"
```

### 7. Header Alignment

**Preserves existing CSV structure**:

```
Existing CSV columns:  [ID, NAME, CODE]
Staged data columns:   [ID, NAME, CODE, TYPE, EXTRA_FIELD]

Append result:
  - Write ID, NAME, CODE from staged data
  - Fill TYPE with "" (missing in original)
  - Ignore EXTRA_FIELD (not in original)
  - Maintain column order from original CSV
```

**Why?**: CSV consumers expect exact column order

---

## Validation Rules

### Type Coercion

```python
# UUID
"abc-123-def" → Validated against UUID regex
"invalid"     → ✗ Error

# Integer
"42"   → 42 ✓
"42.0" → 42 ✓ (float coerced to int)
"abc"  → ✗ Error

# Decimal
"3.14" → 3.14 ✓
"5"    → 5.0 ✓

# Boolean
"true" / "1" / "yes" / "t" / "y" → True ✓
"false" / "0" / "no" / "f" / "n" → False ✓
(case-insensitive)

# Timestamp
"2025-11-13T10:30:00Z" → ISO 8601 ✓
"13/11/2025"           → Parsed ✓
```

### Enum Validation

**Schema**:

```cds
entity PROJECTS {
  TYPE: String enum { solar; wind; hybrid };
}
```

**Validation**:

```python
TYPE = "solar"   → ✓
TYPE = "SOLAR"   → ✓ (case-insensitive)
TYPE = "nuclear" → ✗ Error: "Invalid enum value 'nuclear'. Allowed: solar, wind, hybrid"
```

### Unique Constraints

**Schema**:

```cds
@assert.unique: {unique_vendor: [CODE]}
entity VENDORS {
  CODE: String;
}
```

**Validation**:

```python
# Case-insensitive multi-column uniqueness
Row 1: CODE = "ABC123" → ✓
Row 2: CODE = "abc123" → ✗ Duplicate (same as Row 1)
Row 3: CODE = "XYZ789" → ✓

# Multi-column unique constraint
@assert.unique: {unique_project: [NAME, TYPE, CATEGORY]}
Row 1: NAME="P1", TYPE="solar", CATEGORY="new"     → ✓
Row 2: NAME="P1", TYPE="SOLAR", CATEGORY="NEW"     → ✗ Duplicate
Row 3: NAME="P1", TYPE="wind", CATEGORY="new"      → ✓ (different TYPE)
```

### XOR Rules (UNITSCOPE)

**Schema**:

```cds
entity UNITSCOPE {
  RFI_ID: UUID;
  NC_ID:  UUID;
  // Must have one and only one
}
```

**Validation**:

```python
RFI_ID = "abc", NC_ID = ""     → ✓
RFI_ID = "",    NC_ID = "def"  → ✓
RFI_ID = "abc", NC_ID = "def"  → ✗ Error: "Both RFI_ID and NC_ID provided"
RFI_ID = "",    NC_ID = ""     → ✗ Error: "Neither RFI_ID nor NC_ID provided"
```

---

## Error Handling

### Validation Errors

**FK Resolution Failure**:

```
Row 91: Could not resolve FK 'VENDOR_ID'
  Lookup: VENDORS.CODE = 'MISSING123'
  Reason: Vendor code not found in VENDORS.csv
```

**Unique Constraint Violation**:

```
Row 12: Duplicate unique constraint 'unique_so'
  Fields: SO_NUMBER = '4810023149'
  Reason: SO_NUMBER already exists in data/SERVICEORDERS.csv
```

**Invalid Enum Value**:

```
Row 5: Invalid enum value 'nuclear' for field TYPE
  Allowed: solar, wind, hybrid
```

### Recovery Strategies

**1. Fix Data in Excel**

```python
# Add missing vendor codes
# Remove true duplicates
# Correct enum values
```

**2. Use Partial Commit**

```cmd
python -m src.main commit-partial
```

- Appends clean entities
- Skips entities with errors
- Review errors, fix Excel, re-run

**3. Restore from Backup**

```cmd
# List backups
dir backups

# Restore specific backup
Copy-Item backups\2025-11-13_143052\*.csv data\
```

**4. Manual Append (Last Resort)**

```python
# Use append_remaining.py with csv.DictWriter
# Prevents UUID concatenation issues
python append_remaining.py
```

---

## Configuration

### Mapping YAML

```yaml
version: 1
workbook: "Khavda-PhIII-Solar-SO Mapping.xlsx"
mode: append-only

sheets:
  - sheet: "Sheet1"
    entity: SERVICEORDERS
    csvFile: data/CCTECH.DRS.ENTITIES-SERVICEORDERS.csv

    id:
      column: ID
      uuidPolicy: generate_if_blank # or 'preserve'

    columnMap:
      "Excel Column Name": CSV_FIELD
      "Project": NAME
      "SO Number": SO_NUMBER

    lookups:
      PROJECT_ID:
        entity: PROJECTS
        optional: false # Required FK
        match:
          - field: NAME # Match on PROJECTS.NAME
            from: "Project" # Excel column

      VENDOR_ID:
        entity: VENDORS
        optional: true # Optional FK (can be null)
        match:
          - field: CODE
            from: "Vendor Code"

    defaults:
      RFI_COUNT: 0
      NC_COUNT: 0
      STATUS: "pending"
```

### Schema (CDS)

```cds
namespace CCTECH.DRS.ENTITIES;

// Master data entity
@assert.unique: {unique_vendor: [CODE]}
entity VENDORS {
  key ID:         UUID;
      CODE:       String;
      NAME:       String;
      GST_NUMBER: String;
}

// Entity with FK relationship
entity PROJECTS {
  key ID:       UUID;
      SPV_ID:   UUID;                 // Foreign key
      SPV:      Association to SPVS   // CDS association
                  on SPV.ID = $self.SPV_ID;
      NAME:     String;
      TYPE:     String enum { solar; wind; hybrid };
      CATEGORY: String;
}
```

---

## Troubleshooting

### Issue: "Could not resolve FK"

**Error Message**:

```
Row 91: Could not resolve FK 'VENDOR_ID'
  Lookup: VENDORS.CODE = 'ABC123'
```

**Cause**: Natural key not found in target entity

**Fixes**:

1. Verify target entity is staged first (check ingestion order)
2. Check Excel column has correct value
3. Verify vendor exists in `data/VENDORS.csv`
4. If optional, mark as `optional: true` in mapping

### Issue: "Unique constraint violated"

**Error Message**:

```
Row 12: Duplicate unique constraint 'unique_so'
  Fields: SO_NUMBER = '4810023149'
```

**Cause**: Duplicate natural key in Excel or existing CSV

**Fixes**:

1. Remove duplicate rows from Excel
2. Set duplicate policy to `'skip'` in `policy.py`
3. Use `commit-partial` to skip duplicates

### Issue: "Empty key fields"

**Error Message**:

```
Row 45: Skipped due to empty dedup key fields: ['NAME']
```

**Cause**: Dedup key columns are blank in Excel

**Fixes**:

1. Fill required columns in Excel
2. Remove invalid rows with blank keys
3. Verify columnMap points to correct Excel columns

### Issue: UUID concatenation in output

**Example**:

```csv
ID,NAME
abc-123def-456,XYZ
```

**Cause**: Manual text append without CSV writer

**Fix**: Use `csv.DictWriter` or `append_remaining.py`

```python
import csv
with open('file.csv', 'a', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'NAME'])
    writer.writerow({'ID': 'abc-123', 'NAME': 'XYZ'})
```

### Issue: "Skipped due to duplicate" counted as error

**Context**: `commit` command fails even though data is valid

**Cause**: Duplicate policy set to `'skip'` logs as info but counted as error

**Fix**: Use `commit-partial` instead of `commit`

- `commit-partial` appends entities with 0 errors
- Entities with only "skipped due to duplicate" messages are treated as clean

---

## Best Practices

### 1. Always Run Stage First

```cmd
# Dry-run validation before committing
python -m src.main stage

# Review output
# Check staging/*.csv files
# Fix errors in Excel if needed
```

### 2. Use Partial Commit for Incremental Loads

```cmd
# When some entities have errors
python -m src.main commit-partial

# Append clean entities immediately
# Fix errors and re-run for remaining
```

### 3. Keep Backups

- Never delete `backups/` folder before verifying append
- Check latest backup timestamp matches commit time
- Test restore process periodically

### 4. Fix Data Quality in Excel

**Before importing**:

- ✅ Fill required fields (vendor codes, project names)
- ✅ Remove true duplicates (not master data repeats)
- ✅ Use consistent casing for natural keys
- ✅ Validate enum values match schema
- ✅ Check FK references exist

### 5. Review Mapping Configuration

**Checklist**:

- ✅ columnMap matches Excel headers exactly (including line breaks)
- ✅ FK lookup natural keys are correct
- ✅ optional: true for nullable FKs
- ✅ Defaults provided for optional fields
- ✅ uuidPolicy set correctly

### 6. Monitor Staging Reports

```
✓ PLOTS: 9 valid, 0 errors           ← Clean, ready to commit
✓ VENDORS: 59 valid, 0 errors        ← Clean, ready to commit
⚠ SERVICEORDERS: 254 valid, 1 error  ← Review error, fix Excel
```

**Action**:

- Entities with 0 errors: Commit immediately
- Entities with errors: Review logs, fix data, re-stage

### 7. Incremental Development

**Workflow**:

1. Start with 1 entity (e.g., VENDORS)
2. Configure mapping, stage, commit
3. Add next entity (e.g., PROJECTS with VENDOR_ID FK)
4. Repeat until all entities staged

**Benefits**:

- Easier debugging
- Faster iteration
- Incremental validation

### 8. Use Version Control

```cmd
# Commit mapping changes
git add config/mapping_generated.yaml
git commit -m "Add SERVICEORDERS mapping with optional VENDOR_ID"

# Commit schema changes
git add schema.cds
git commit -m "Add SOLARPROJECTATTRIBUTES entity"
```

---

## Performance

### Optimization Strategies

1. **Caching**: FK resolver caches entity data per pass (avoid re-reading CSVs)
2. **Batch Validation**: Validate all rows before staging (fail fast)
3. **Incremental Staging**: Only re-stage entities with FK errors
4. **Early Termination**: Stop iterating when no improvement detected

### Typical Metrics

- **255 Excel rows** → 8 entities → **347 staged rows** (after dedup)
- **3 passes** to resolve all FKs (typical)
- **~5 seconds** end-to-end (includes validation + staging + append)

### Scalability

- **10,000 Excel rows**: ~20 seconds
- **100,000 Excel rows**: ~3-5 minutes
- Bottleneck: FK lookups (linear search in CSV)
- Future: Index natural keys for O(1) lookups

---

## Dependencies

```txt
openpyxl    # Excel reading (3-row headers)
PyYAML      # Mapping configuration
csv         # CSV handling (stdlib)
uuid        # UUID generation (stdlib)
datetime    # Timestamps (stdlib)
pathlib     # Path handling (stdlib)
re          # Regex for CDS parsing (stdlib)
json        # Schema serialization (stdlib)
```

**Install**:

```cmd
pip install openpyxl pyyaml
```

---

## License & Credits

Built for Pulse Data Management System - Enterprise ETL Pipeline

**Technologies**: Python 3.x, SAP CDS schema, openpyxl, PyYAML

**Last Updated**: November 13, 2025
