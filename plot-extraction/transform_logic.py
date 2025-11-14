"""
Transformation Logic Module
============================

This module provides functions to parse and transform:
1. Folder names → Plot names
2. Excel filenames → Block names
3. Table/Inverter names → Clean names (strip block prefix)

Date: November 14, 2025
"""

import re
from pathlib import Path
from typing import Optional, Dict, Tuple


class TransformationError(Exception):
    """Custom exception for transformation errors."""
    pass


def folder_to_plot_name(folder_name: str) -> Optional[str]:
    """
    Transform folder name to plot name.
    
    Args:
        folder_name: Folder name like "A16a - 50 MW"
        
    Returns:
        Plot name like "A-16a" or None if pattern doesn't match
        
    Examples:
        >>> folder_to_plot_name("A16a - 50 MW")
        'A-16a'
        >>> folder_to_plot_name("A16b - 200 MW")
        'A-16b'
        >>> folder_to_plot_name("S05b - 167 MW")
        'S-05b'
    """
    # Extract the plot identifier from folder name (before the dash)
    # Pattern: "A16a - 50 MW" → extract "A16a"
    parts = folder_name.split('-')
    if not parts:
        return None
    
    plot_raw = parts[0].strip()
    
    # Transform: A16a → A-16a (insert hyphen after first letter)
    # Pattern: Single letter + digits + optional letter
    match = re.match(r'^([A-Z])(\d+)([a-z]?)$', plot_raw, re.IGNORECASE)
    if match:
        letter, digits, suffix = match.groups()
        return f"{letter.upper()}-{digits}{suffix.lower()}"
    
    return None


def filename_to_block_name(filename: str) -> Optional[str]:
    """
    Extract block name from Excel filename.
    
    Args:
        filename: Excel filename like "603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx"
        
    Returns:
        Block name like "BL01" or None if pattern doesn't match
        
    Examples:
        >>> filename_to_block_name("603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx")
        'BL01'
        >>> filename_to_block_name("603C-LT Cable Routing A16a-BL04-R0-30032025_DWGData.xlsx")
        'BL04'
    """
    # Pattern: *-BL##-*.xlsx
    match = re.search(r'-BL(\d+)-', filename, re.IGNORECASE)
    if match:
        block_num = match.group(1)
        return f"BL{block_num}"
    
    return None


def filename_to_plot_name(filename: str) -> Optional[str]:
    """
    Extract plot name from Excel filename (as validation).
    
    Args:
        filename: Excel filename like "603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx"
        
    Returns:
        Plot name like "A-16a" or None if pattern doesn't match
        
    Examples:
        >>> filename_to_plot_name("603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx")
        'A-16a'
    """
    # Extract plot identifier from filename
    # Look for pattern like "A16a" or "S05b" (must be followed by -BL to avoid matching R0)
    match = re.search(r'-([A-Z]\d+[a-z]?)-BL', filename, re.IGNORECASE)
    if match:
        plot_raw = match.group(1)
        # Transform: A16a → A-16a
        transform_match = re.match(r'^([A-Z])(\d+)([a-z]?)$', plot_raw, re.IGNORECASE)
        if transform_match:
            letter, digits, suffix = transform_match.groups()
            return f"{letter.upper()}-{digits}{suffix.lower()}"
    
    return None


def extract_clean_name(prefixed_name: str) -> Optional[str]:
    """
    Extract clean name by removing block prefix.
    
    Args:
        prefixed_name: Name with block prefix like "B01-R42-S01" or "B04-I41"
        
    Returns:
        Clean name like "R42-S01" or "I41" or None if pattern doesn't match
        
    Examples:
        >>> extract_clean_name("B01-R42-S01")
        'R42-S01'
        >>> extract_clean_name("B04-I41")
        'I41'
        >>> extract_clean_name("B02-R30-T05")
        'R30-T05'
        >>> extract_clean_name("BO4-R31-S01")
        'R31-S01'
    """
    # Pattern: B## or BO# prefix followed by dash and the actual name
    # Handle both B01- and BO4- patterns
    match = re.match(r'^B[O]?\d+-(.+)$', prefixed_name, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # If no prefix found, return the name as-is (might already be clean)
    return prefixed_name


def determine_type_from_name(name: str) -> str:
    """
    Determine the type (TABLE or INVERTER) from the name.
    
    Args:
        name: Clean name like "R42-S01" or "I41"
        
    Returns:
        "TABLE" or "INVERTER"
        
    Examples:
        >>> determine_type_from_name("R42-S01")
        'TABLE'
        >>> determine_type_from_name("R30-T05")
        'TABLE'
        >>> determine_type_from_name("I41")
        'INVERTER'
        >>> determine_type_from_name("I05")
        'INVERTER'
    """
    # Inverter pattern: I## or I#
    if re.match(r'^I\d+$', name, re.IGNORECASE):
        return "INVERTER"
    
    # Table pattern: R##-S## or R##-T##
    if re.match(r'^R\d+-[ST]\d+$', name, re.IGNORECASE):
        return "TABLE"
    
    # Default to TABLE if pattern is unclear
    return "TABLE"


def parse_excel_filename(filepath: str) -> Dict[str, Optional[str]]:
    """
    Parse Excel filename to extract all relevant information.
    
    Args:
        filepath: Full path or filename
        
    Returns:
        Dictionary with keys: 'plot_name', 'block_name', 'filename'
        
    Examples:
        >>> result = parse_excel_filename("603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx")
        >>> result['plot_name']
        'A-16a'
        >>> result['block_name']
        'BL01'
    """
    filename = Path(filepath).name
    
    return {
        'filename': filename,
        'plot_name': filename_to_plot_name(filename),
        'block_name': filename_to_block_name(filename)
    }


def validate_plot_consistency(folder_plot: str, filename_plot: str) -> bool:
    """
    Validate that plot name from folder matches plot name from filename.
    
    Args:
        folder_plot: Plot name extracted from folder
        filename_plot: Plot name extracted from filename
        
    Returns:
        True if they match, False otherwise
        
    Examples:
        >>> validate_plot_consistency("A-16a", "A-16a")
        True
        >>> validate_plot_consistency("A-16a", "A-16b")
        False
    """
    if folder_plot is None or filename_plot is None:
        return False
    
    return folder_plot.upper() == filename_plot.upper()


def extract_table_and_inverter(row_data: Tuple[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract clean table and inverter names from a data row.
    
    Args:
        row_data: Tuple of (table_with_prefix, inverter_with_prefix)
        
    Returns:
        Tuple of (clean_table_name, clean_inverter_name)
        
    Examples:
        >>> extract_table_and_inverter(("B01-R42-S01", "B01-I45"))
        ('R42-S01', 'I45')
        >>> extract_table_and_inverter(("B04-R31-S01", "B04-I41"))
        ('R31-S01', 'I41')
    """
    table_raw, inverter_raw = row_data
    
    table_clean = None
    inverter_clean = None
    
    if table_raw and str(table_raw).strip():
        table_clean = extract_clean_name(str(table_raw).strip())
    
    if inverter_raw and str(inverter_raw).strip():
        inverter_clean = extract_clean_name(str(inverter_raw).strip())
    
    return table_clean, inverter_clean


# Test functions
def run_tests():
    """Run unit tests for all transformation functions."""
    print("="*80)
    print("TRANSFORMATION LOGIC TESTS")
    print("="*80)
    
    # Test 1: Folder to plot name
    print("\n1. Folder Name → Plot Name")
    print("-" * 80)
    test_folders = [
        ("A16a - 50 MW", "A-16a"),
        ("A16b - 200 MW", "A-16b"),
        ("A16c - 167 MW", "A-16c"),
        ("A16d - 333 MW", "A-16d"),
        ("S05b - 100 MW", "S-05b"),
    ]
    
    for folder, expected in test_folders:
        result = folder_to_plot_name(folder)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{folder}' → '{result}' (expected: '{expected}')")
    
    # Test 2: Filename to block name
    print("\n2. Filename → Block Name")
    print("-" * 80)
    test_filenames = [
        ("603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx", "BL01"),
        ("603C-LT Cable Routing-A16a-BL02-R0-30032025_DWGData.xlsx", "BL02"),
        ("603C-LT Cable Routing A16a-BL04-R0-30032025_DWGData.xlsx", "BL04"),
        ("603C-LT Cable Routing-A16a-BL03-R0-30032025_DWGData.xlsx", "BL03"),
    ]
    
    for filename, expected in test_filenames:
        result = filename_to_block_name(filename)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{filename[:50]}...' → '{result}' (expected: '{expected}')")
    
    # Test 3: Filename to plot name
    print("\n3. Filename → Plot Name")
    print("-" * 80)
    test_filenames_plot = [
        ("603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx", "A-16a"),
        ("603C-LT Cable Routing-A16b-BL02-R0-30032025_DWGData.xlsx", "A-16b"),
    ]
    
    for filename, expected in test_filenames_plot:
        result = filename_to_plot_name(filename)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{filename[:50]}...' → '{result}' (expected: '{expected}')")
    
    # Test 4: Extract clean names
    print("\n4. Prefixed Name → Clean Name")
    print("-" * 80)
    test_names = [
        ("B01-R42-S01", "R42-S01"),
        ("B04-R31-S01", "R31-S01"),
        ("B02-I45", "I45"),
        ("B01-I47", "I47"),
        ("BO4-R31-S01", "R31-S01"),  # Alternative prefix pattern
        ("B03-R40-T01", "R40-T01"),
    ]
    
    for prefixed, expected in test_names:
        result = extract_clean_name(prefixed)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{prefixed}' → '{result}' (expected: '{expected}')")
    
    # Test 5: Determine type
    print("\n5. Name → Type Detection")
    print("-" * 80)
    test_types = [
        ("R42-S01", "TABLE"),
        ("R31-T05", "TABLE"),
        ("I45", "INVERTER"),
        ("I41", "INVERTER"),
        ("R40-S02", "TABLE"),
    ]
    
    for name, expected in test_types:
        result = determine_type_from_name(name)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{name}' → '{result}' (expected: '{expected}')")
    
    # Test 6: Extract table and inverter from row
    print("\n6. Row Data → Clean Names")
    print("-" * 80)
    test_rows = [
        (("B01-R42-S01", "B01-I45"), ("R42-S01", "I45")),
        (("B04-R31-S01", "B04-I41"), ("R31-S01", "I41")),
        (("B02-R40-S01", "B02-I47"), ("R40-S01", "I47")),
    ]
    
    for row_data, expected in test_rows:
        result = extract_table_and_inverter(row_data)
        status = "✅" if result == expected else "❌"
        print(f"{status} {row_data} → {result} (expected: {expected})")
    
    # Test 7: Plot consistency validation
    print("\n7. Plot Consistency Validation")
    print("-" * 80)
    test_consistency = [
        (("A-16a", "A-16a"), True),
        (("A-16a", "A-16b"), False),
        (("A-16a", None), False),
    ]
    
    for (folder_plot, file_plot), expected in test_consistency:
        result = validate_plot_consistency(folder_plot, file_plot)
        status = "✅" if result == expected else "❌"
        print(f"{status} Folder: '{folder_plot}', File: '{file_plot}' → {result} (expected: {expected})")
    
    print("\n" + "="*80)
    print("✅ All tests completed!")
    print("="*80)


if __name__ == "__main__":
    run_tests()
