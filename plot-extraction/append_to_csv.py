"""
CSV Append Script - Step 5
===========================

Append new design elements to CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv
with backup, validation, and summary reporting.

Date: November 14, 2025
"""

import csv
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import defaultdict, Counter


def create_backup(csv_path: Path) -> Path:
    """
    Create a timestamped backup of the CSV file.
    
    Args:
        csv_path: Path to CSV file to backup
        
    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_path.parent / f"{csv_path.stem}_backup_{timestamp}.csv"
    shutil.copy2(csv_path, backup_path)
    return backup_path


def count_csv_rows(csv_path: Path) -> int:
    """
    Count rows in CSV file (excluding header).
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Number of data rows
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        return sum(1 for line in f) - 1  # Exclude header


def load_new_elements(csv_path: Path) -> List[Dict[str, str]]:
    """
    Load new elements from CSV file.
    
    Args:
        csv_path: Path to new_design_elements.csv
        
    Returns:
        List of element dictionaries
    """
    elements = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            elements.append(row)
    return elements


def append_to_csv(
    target_csv: Path,
    new_elements: List[Dict[str, str]],
    fieldnames: List[str]
) -> int:
    """
    Append new elements to target CSV file.
    
    Args:
        target_csv: Path to DESIGNELEMENTS.csv
        new_elements: List of element dictionaries to append
        fieldnames: CSV column order
        
    Returns:
        Number of rows appended
    """
    with open(target_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for element in new_elements:
            writer.writerow(element)
    
    return len(new_elements)


def generate_summary_report(
    new_elements: List[Dict[str, str]],
    output_path: Path
) -> Dict:
    """
    Generate detailed summary report of appended elements.
    
    Args:
        new_elements: List of element dictionaries
        output_path: Path to save summary report
        
    Returns:
        Dictionary with summary statistics
    """
    # Overall statistics
    total_count = len(new_elements)
    type_counts = Counter(e['TYPE'] for e in new_elements)
    project_counts = Counter(e['PROJECT_ID'] for e in new_elements)
    
    # Project name mapping
    project_names = {
        'e0c901b8-3037-4bc1-885e-654f92aa4d1d': 'A-16a',
        'c9ce1fed-043f-4f41-92df-856028a07580': 'A-16b',
        'd2645c47-02aa-4fb5-8d19-5aabf00358c7': 'A-16c',
        'a45b536a-057b-491e-9759-42430dd20112': 'A-16d'
    }
    
    # Detailed breakdown by project and block
    project_breakdown = defaultdict(lambda: {
        'plots': 0,
        'blocks': 0,
        'tables': 0,
        'inverters': 0,
        'blocks_detail': defaultdict(lambda: {'tables': 0, 'inverters': 0})
    })
    
    for element in new_elements:
        project_id = element['PROJECT_ID']
        element_type = element['TYPE']
        
        if element_type == 'PLOT':
            project_breakdown[project_id]['plots'] += 1
        elif element_type == 'BLOCK':
            project_breakdown[project_id]['blocks'] += 1
        elif element_type == 'TABLE':
            project_breakdown[project_id]['tables'] += 1
            # Find parent BLOCK
            parent_id = element['PARENT_ID']
            block = next((e for e in new_elements if e['ID'] == parent_id), None)
            if block:
                project_breakdown[project_id]['blocks_detail'][block['NAME']]['tables'] += 1
        elif element_type == 'INVERTER':
            project_breakdown[project_id]['inverters'] += 1
            # Find parent BLOCK
            parent_id = element['PARENT_ID']
            block = next((e for e in new_elements if e['ID'] == parent_id), None)
            if block:
                project_breakdown[project_id]['blocks_detail'][block['NAME']]['inverters'] += 1
    
    # Generate report text
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("APPEND SUMMARY REPORT")
    report_lines.append("="*80)
    report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    report_lines.append(f"\n{'='*80}")
    report_lines.append("OVERALL STATISTICS")
    report_lines.append("="*80)
    report_lines.append(f"\nTotal elements appended: {total_count:,}")
    report_lines.append(f"\nBreakdown by type:")
    report_lines.append(f"   PLOTs:     {type_counts['PLOT']:,}")
    report_lines.append(f"   BLOCKs:    {type_counts['BLOCK']:,}")
    report_lines.append(f"   TABLEs:    {type_counts['TABLE']:,}")
    report_lines.append(f"   INVERTERs: {type_counts['INVERTER']:,}")
    
    report_lines.append(f"\n{'='*80}")
    report_lines.append("BREAKDOWN BY PROJECT/PLOT")
    report_lines.append("="*80)
    
    for project_id in sorted(project_breakdown.keys()):
        plot_name = project_names.get(project_id, project_id[:8] + "...")
        breakdown = project_breakdown[project_id]
        
        total_project = breakdown['plots'] + breakdown['blocks'] + breakdown['tables'] + breakdown['inverters']
        
        report_lines.append(f"\n📊 {plot_name} (PROJECT_ID: {project_id})")
        report_lines.append(f"   Total elements: {total_project:,}")
        report_lines.append(f"   PLOTs: {breakdown['plots']}, BLOCKs: {breakdown['blocks']}, TABLEs: {breakdown['tables']}, INVERTERs: {breakdown['inverters']}")
        
        if breakdown['blocks_detail']:
            report_lines.append(f"\n   Breakdown by BLOCK:")
            for block_name in sorted(breakdown['blocks_detail'].keys()):
                block_data = breakdown['blocks_detail'][block_name]
                block_total = block_data['tables'] + block_data['inverters']
                report_lines.append(f"      {block_name}: {block_total:,} elements (TABLEs: {block_data['tables']}, INVERTERs: {block_data['inverters']})")
    
    report_lines.append(f"\n{'='*80}")
    report_lines.append("HIERARCHY VERIFICATION")
    report_lines.append("="*80)
    
    # Verify parent-child relationships
    element_by_id = {e['ID']: e for e in new_elements}
    orphans = []
    
    for element in new_elements:
        if element['TYPE'] == 'PLOT':
            # PLOTs should have empty PARENT_ID
            if element['PARENT_ID']:
                orphans.append(f"PLOT {element['NAME']} has non-empty PARENT_ID")
        elif element['TYPE'] in ['BLOCK', 'TABLE', 'INVERTER']:
            # Others should have valid PARENT_ID
            parent_id = element['PARENT_ID']
            if not parent_id:
                orphans.append(f"{element['TYPE']} {element['NAME']} has empty PARENT_ID")
            elif parent_id not in element_by_id:
                orphans.append(f"{element['TYPE']} {element['NAME']} has invalid PARENT_ID (not in new elements)")
    
    if orphans:
        report_lines.append(f"\n⚠️  Found {len(orphans)} hierarchy issues:")
        for orphan in orphans[:10]:  # Show first 10
            report_lines.append(f"   {orphan}")
        if len(orphans) > 10:
            report_lines.append(f"   ... and {len(orphans) - 10} more")
    else:
        report_lines.append(f"\n✅ All parent-child relationships validated")
    
    report_lines.append(f"\n{'='*80}")
    report_lines.append("✅ APPEND COMPLETED SUCCESSFULLY!")
    report_lines.append("="*80)
    
    # Save report to file
    report_text = "\n".join(report_lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    # Return statistics
    return {
        'total_count': total_count,
        'type_counts': dict(type_counts),
        'project_counts': dict(project_counts),
        'project_breakdown': dict(project_breakdown),
        'orphans': len(orphans)
    }


def main():
    """Main append function."""
    
    base_path = Path(r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction")
    data_path = base_path / "data"
    output_path = base_path / "output"
    
    # File paths
    target_csv = data_path / "CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv"
    new_elements_csv = output_path / "new_design_elements.csv"
    summary_report_path = output_path / "append_summary_report.txt"
    
    print("="*80)
    print("CSV APPEND - STEP 5")
    print("="*80)
    
    # Validate files exist
    if not target_csv.exists():
        print(f"\n❌ Error: Target CSV not found: {target_csv}")
        return False
    
    if not new_elements_csv.exists():
        print(f"\n❌ Error: New elements CSV not found: {new_elements_csv}")
        return False
    
    # Count existing rows
    print(f"\n📊 Current state:")
    existing_rows = count_csv_rows(target_csv)
    print(f"   Existing rows in DESIGNELEMENTS.csv: {existing_rows:,}")
    
    # Load new elements
    print(f"\n📄 Loading new elements from: {new_elements_csv.name}")
    new_elements = load_new_elements(new_elements_csv)
    print(f"   ✅ Loaded {len(new_elements):,} new elements")
    
    # Create backup
    print(f"\n💾 Creating backup...")
    backup_path = create_backup(target_csv)
    print(f"   ✅ Backup created: {backup_path.name}")
    
    # Append to CSV
    print(f"\n📝 Appending to DESIGNELEMENTS.csv...")
    fieldnames = ['ID', 'PROJECT_ID', 'NAME', 'TYPE', 'PARENT_ID']
    rows_appended = append_to_csv(target_csv, new_elements, fieldnames)
    print(f"   ✅ Appended {rows_appended:,} rows")
    
    # Verify final count
    print(f"\n🔍 Verifying final count...")
    final_rows = count_csv_rows(target_csv)
    expected_rows = existing_rows + rows_appended
    
    if final_rows == expected_rows:
        print(f"   ✅ Verification passed!")
        print(f"      Before: {existing_rows:,}")
        print(f"      Added:  {rows_appended:,}")
        print(f"      After:  {final_rows:,}")
    else:
        print(f"   ⚠️  Row count mismatch!")
        print(f"      Expected: {expected_rows:,}")
        print(f"      Actual:   {final_rows:,}")
        print(f"      Difference: {final_rows - expected_rows:,}")
    
    # Generate summary report
    print(f"\n📋 Generating summary report...")
    stats = generate_summary_report(new_elements, summary_report_path)
    print(f"   ✅ Report saved to: {summary_report_path.name}")
    
    # Print summary to console
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)
    print(f"\nTotal elements appended: {stats['total_count']:,}")
    print(f"\nBy type:")
    for element_type, count in stats['type_counts'].items():
        print(f"   {element_type}: {count:,}")
    
    print(f"\nBy project/plot:")
    project_names = {
        'e0c901b8-3037-4bc1-885e-654f92aa4d1d': 'A-16a',
        'c9ce1fed-043f-4f41-92df-856028a07580': 'A-16b',
        'd2645c47-02aa-4fb5-8d19-5aabf00358c7': 'A-16c',
        'a45b536a-057b-491e-9759-42430dd20112': 'A-16d'
    }
    for project_id, count in stats['project_counts'].items():
        plot_name = project_names.get(project_id, project_id[:8] + "...")
        print(f"   {plot_name}: {count:,}")
    
    if stats['orphans'] > 0:
        print(f"\n⚠️  Found {stats['orphans']} hierarchy issues - check report for details")
    else:
        print(f"\n✅ All hierarchy relationships validated")
    
    print(f"\n{'='*80}")
    print(f"✅ APPEND COMPLETED SUCCESSFULLY!")
    print("="*80)
    print(f"\n📁 Files:")
    print(f"   Target CSV:  {target_csv}")
    print(f"   Backup:      {backup_path}")
    print(f"   Report:      {summary_report_path}")
    
    return True


if __name__ == "__main__":
    main()
