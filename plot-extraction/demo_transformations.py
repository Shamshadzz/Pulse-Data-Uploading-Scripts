"""
Demonstration: Transformation Logic with Real File Paths
=========================================================

This script demonstrates how the transformation logic works with actual
files from the drawing_data directory.
"""

from pathlib import Path
from transform_logic import (
    folder_to_plot_name,
    filename_to_block_name,
    filename_to_plot_name,
    parse_excel_filename,
    validate_plot_consistency,
    extract_clean_name,
    determine_type_from_name
)


def demonstrate_transformations():
    """Demonstrate transformations with real file paths."""
    
    print("="*80)
    print("TRANSFORMATION LOGIC DEMONSTRATION")
    print("Using Real Files from drawing_data/")
    print("="*80)
    
    # Get real folders
    base_path = Path(r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction\drawing_data")
    
    if not base_path.exists():
        print(f"❌ Base path not found: {base_path}")
        return
    
    folders = [d for d in base_path.iterdir() if d.is_dir()]
    
    print(f"\n📁 Found {len(folders)} plot folders\n")
    
    for folder in folders:
        print("="*80)
        print(f"📂 Folder: {folder.name}")
        print("="*80)
        
        # Transform folder name to plot name
        plot_name = folder_to_plot_name(folder.name)
        print(f"   Plot Name: {plot_name}")
        
        # Get Excel files in this folder
        excel_files = list(folder.glob("*.xlsx"))
        print(f"   Excel Files: {len(excel_files)}")
        
        for excel_file in excel_files[:2]:  # Show first 2 files
            print(f"\n   📄 File: {excel_file.name}")
            
            # Parse filename
            parsed = parse_excel_filename(excel_file.name)
            print(f"      Block Name: {parsed['block_name']}")
            print(f"      Plot from File: {parsed['plot_name']}")
            
            # Validate consistency
            consistent = validate_plot_consistency(plot_name, parsed['plot_name'])
            status = "✅" if consistent else "❌"
            print(f"      Plot Consistency: {status} {consistent}")
            
            # Show hierarchy that would be created
            print(f"\n      📊 Hierarchy to be created:")
            print(f"         PLOT: {plot_name}")
            print(f"           └─ BLOCK: {parsed['block_name']}")
            print(f"               ├─ TABLE: R42-S01 (example)")
            print(f"               ├─ TABLE: R41-S01 (example)")
            print(f"               ├─ INVERTER: I45 (example)")
            print(f"               └─ INVERTER: I46 (example)")
        
        if len(excel_files) > 2:
            print(f"\n   ... and {len(excel_files) - 2} more files")
        
        print()
    
    # Demonstrate name extraction with sample data
    print("\n" + "="*80)
    print("📋 Sample Data Transformation")
    print("="*80)
    
    sample_rows = [
        ("B01-R42-S01", "B01-I45"),
        ("B04-R31-S01", "B04-I41"),
        ("B02-R40-S01", "B02-I47"),
        ("B03-R39-T02", "B03-I42"),
    ]
    
    print("\nOriginal Excel Data → Clean Names + Types:")
    print("-" * 80)
    print(f"{'Excel Table':<20} {'Excel Inverter':<20} {'Clean Table':<15} {'Type':<10} {'Clean Inv.':<12} {'Type':<10}")
    print("-" * 80)
    
    for table_raw, inv_raw in sample_rows:
        table_clean = extract_clean_name(table_raw)
        table_type = determine_type_from_name(table_clean)
        
        inv_clean = extract_clean_name(inv_raw)
        inv_type = determine_type_from_name(inv_clean)
        
        print(f"{table_raw:<20} {inv_raw:<20} {table_clean:<15} {table_type:<10} {inv_clean:<12} {inv_type:<10}")
    
    print("\n" + "="*80)
    print("✅ Demonstration complete!")
    print("="*80)


if __name__ == "__main__":
    demonstrate_transformations()
