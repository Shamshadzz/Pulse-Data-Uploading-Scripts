"""Test FK resolver with staging data."""
import json
from pathlib import Path
from src.fk_resolver import FKResolver

# Load schema
with open('build/schema.json') as f:
    schema = json.load(f)

# Create FK resolver WITH staging_dir
data_dir = Path('data')
staging_dir = Path('staging')
resolver = FKResolver(data_dir, schema, staging_dir)

# Test lookup for "Google Hybrid (Solar)"
test_project = "Google Hybrid (Solar)"
match_fields = [{'field': 'NAME', 'from': 'test_project'}]
row_values = {'test_project': test_project}

project_id = resolver.lookup_id('PROJECTS', match_fields, row_values)
print(f"Looking up PROJECT_ID for '{test_project}':")
print(f"  Result: {project_id}")

if project_id:
    print("  ✅ Found!")
else:
    print("  ❌ Not found")
    
    # Debug: check what's in the cache
    projects = resolver._load_entity_data('PROJECTS')
    print(f"\n  Debug: {len(projects)} total PROJECTS loaded")
    print("  First 10 project names:")
    for i, p in enumerate(projects[:10], 1):
        print(f"    {i}. '{p.get('NAME', '')}' (ID: {p.get('ID', '')[:8]}...)")
    
    # Check if our target is there
    matches = [p for p in projects if p.get('NAME', '').strip().upper() == test_project.upper()]
    if matches:
        print(f"\n  ⚠️  Found {len(matches)} match(es) in data but lookup failed!")
        print(f"     Match: {matches[0]}")
    else:
        print(f"\n  ❌ '{test_project}' not in loaded data")

# Test more projects from errors
print("\n" + "="*60)
print("Testing all error-prone projects:")
test_projects = [
    "Google Hybrid (Solar)",
    "MLP T1 J&K",
    "MLP T1 CG",
    "MLP T1 TN",
    "MLP T1 OR"
]

for proj in test_projects:
    row_values = {'test_project': proj}
    proj_id = resolver.lookup_id('PROJECTS', match_fields, row_values)
    status = "✅" if proj_id else "❌"
    print(f"{status} '{proj}': {proj_id[:8] if proj_id else 'NOT FOUND'}...")
