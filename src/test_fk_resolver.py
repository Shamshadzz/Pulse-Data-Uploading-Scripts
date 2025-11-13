"""
Test FK resolver with sample data from Excel.
"""
import json
from pathlib import Path
from src.fk_resolver import FKResolver
from src.introspect_excel import introspect_workbook


def test_fk_resolution():
    root = Path(__file__).parent.parent
    schema_path = root / 'build' / 'schema.json'
    data_dir = root / 'data'
    workbook_path = root / 'Khavda Phase-3 Solar_Projects and SO Data (1).xlsx'
    
    # Load schema
    with open(schema_path) as f:
        schema = json.load(f)
    
    # Introspect Excel to get sample row (with 3-row headers)
    excel_info = introspect_workbook(str(workbook_path), header_rows=3)
    
    print("Testing FK Resolver")
    print("=" * 60)
    
    # Load first data row from Excel (data starts at row 4 after 3-row header)
    import openpyxl
    wb = openpyxl.load_workbook(str(workbook_path), read_only=True, data_only=True)
    sheet_name = excel_info['sheets'][0]['name']
    ws = wb[sheet_name]
    
    # Get merged headers from introspection
    headers = excel_info['sheets'][0]['headers']
    
    # Get first data row (row 4, since rows 1-3 are headers)
    data_row = next(ws.iter_rows(min_row=4, max_row=4, values_only=True), None)
    if data_row:
        row_dict = {headers[i]: data_row[i] for i in range(len(headers)) if i < len(data_row)}
        
        print(f"\nSample Excel row:")
        for k, v in row_dict.items():
            if v:
                print(f"  {k}: {v}")
        
        print(f"\n" + "=" * 60)
        
        # Test FK resolution for different entities
        resolver = FKResolver(data_dir, schema)
        
        # Test CLUSTERS lookup
        print("\nTest 1: Lookup CLUSTERS by NAME")
        cluster_name = row_dict.get('Cluster', '')
        if cluster_name:
            cluster_id = resolver.lookup_id(
                'CLUSTERS',
                [{'field': 'NAME', 'from': 'Cluster'}],
                row_dict
            )
            print(f"  Cluster '{cluster_name}' → ID: {cluster_id}")
        
        # Test LOCATIONS lookup (requires resolved CLUSTER_ID)
        print("\nTest 2: Lookup LOCATIONS by NAME + resolved CLUSTER_ID")
        location_name = row_dict.get('Location', '')
        if location_name and cluster_id:
            # First resolve cluster, then use it for location lookup
            row_with_cluster_id = {**row_dict, 'CLUSTER_ID': cluster_id}
            location_id = resolver.lookup_id(
                'LOCATIONS',
                [
                    {'field': 'NAME', 'from': 'Location'},
                    {'field': 'CLUSTER_ID', 'from': 'CLUSTER_ID'}
                ],
                row_with_cluster_id
            )
            print(f"  Location '{location_name}' + Cluster '{cluster_id}' → ID: {location_id}")
        
        # Test SPV lookup
        print("\nTest 3: Lookup SPVS by NAME")
        spv_name = row_dict.get('SPV', '')
        if spv_name:
            spv_id = resolver.lookup_id(
                'SPVS',
                [{'field': 'NAME', 'from': 'SPV'}],
                row_dict
            )
            print(f"  SPV '{spv_name}' → ID: {spv_id}")
        
        # Test PROJECT lookup
        print("\nTest 4: Lookup PROJECTS by NAME")
        project_name = row_dict.get('Project', '')
        if project_name:
            project_id = resolver.lookup_id(
                'PROJECTS',
                [{'field': 'NAME', 'from': 'Project'}],
                row_dict
            )
            print(f"  Project '{project_name}' → ID: {project_id}")
    
    wb.close()
    print("\n" + "=" * 60)
    print("✓ FK Resolver tests complete")


if __name__ == '__main__':
    test_fk_resolution()
