"""
Transformation Logic for Plot Extraction ETL Pipeline
======================================================

This module provides transformation functions to:
- Parse folder names to plot names (A16a - 50 MW → A-16a)
- Extract block names from Excel filenames (*-BL04-*.xlsx → BL04)
- Strip block prefixes from table/inverter names (B04-R31-S01 → R31-S01)
- Validate extracted names and patterns

Date: November 14, 2025
"""

import re
from typing import Optional, Dict, Tuple
from pathlib import Path


class PlotTransformer:
    """Handles transformation of folder names to plot names."""
    
    # Pattern to match plot folder names: "A16a - 50 MW", "S08b - 200 MW", etc.
    FOLDER_PATTERN = re.compile(r'^([A-Z])(\d+)([a-z])\s*-\s*(.+)$')
    
    @classmethod
    def folder_to_plot_name(cls, folder_name: str) -> Optional[str]:
        """
        Convert folder name to plot name by inserting hyphen after first letter.
        
        Args:
            folder_name: Folder name like "A16a - 50 MW" or "S08b - 200 MW"
            
        Returns:
            Plot name like "A-16a" or "S-08b", or None if pattern doesn't match
            
        Examples:
            >>> PlotTransformer.folder_to_plot_name("A16a - 50 MW")
            'A-16a'
            >>> PlotTransformer.folder_to_plot_name("S08b - 200 MW")
            'S-08b'
            >>> PlotTransformer.folder_to_plot_name("A16c - 167 MW")
            'A-16c'
        """
        if not folder_name:
            return None
            
        match = cls.FOLDER_PATTERN.match(folder_name.strip())
        if match:
            letter = match.group(1)      # A, S, etc.
            number = match.group(2)      # 16, 08, etc.
            suffix = match.group(3)      # a, b, c, etc.
            # capacity = match.group(4)  # "50 MW", "200 MW", etc. (not used)
            
            return f"{letter}-{number}{suffix}"
        
        return None
    
    @classmethod
    def validate_plot_name(cls, plot_name: str) -> bool:
        """
        Validate that a plot name follows the expected pattern.
        
        Args:
            plot_name: Plot name to validate (e.g., "A-16a")
            
        Returns:
            True if valid, False otherwise
            
        Examples:
            >>> PlotTransformer.validate_plot_name("A-16a")
            True
            >>> PlotTransformer.validate_plot_name("S-08b")
            True
            >>> PlotTransformer.validate_plot_name("Invalid")
            False
        """
        pattern = re.compile(r'^[A-Z]-\d+[a-z]$')
        return bool(pattern.match(plot_name))


class BlockTransformer:
    """Handles extraction of block names from Excel filenames."""
    
    # Pattern to match block names in filenames: -BL01-, -BL04-, etc.
    BLOCK_PATTERN = re.compile(r'-BL(\d+)-', re.IGNORECASE)
    
    @classmethod
    def filename_to_block_name(cls, filename: str) -> Optional[str]:
        """
        Extract block name from Excel filename.
        
        Args:
            filename: Excel filename like "603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx"
            
        Returns:
            Block name like "BL01", or None if pattern not found
            
        Examples:
            >>> BlockTransformer.filename_to_block_name("603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx")
            'BL01'
            >>> BlockTransformer.filename_to_block_name("603C-LT Cable Routing A16a-BL04-R0-30032025_DWGData.xlsx")
            'BL04'
        """
        if not filename:
            return None
            
        match = cls.BLOCK_PATTERN.search(filename)
        if match:
            block_number = match.group(1)  # "01", "04", etc.
            return f"BL{block_number}"
        
        return None
    
    @classmethod
    def validate_block_name(cls, block_name: str) -> bool:
        """
        Validate that a block name follows the expected pattern.
        
        Args:
            block_name: Block name to validate (e.g., "BL01")
            
        Returns:
            True if valid, False otherwise
            
        Examples:
            >>> BlockTransformer.validate_block_name("BL01")
            True
            >>> BlockTransformer.validate_block_name("BL99")
            True
            >>> BlockTransformer.validate_block_name("Invalid")
            False
        """
        pattern = re.compile(r'^BL\d+$', re.IGNORECASE)
        return bool(pattern.match(block_name))


class NameExtractor:
    """Handles extraction of clean names from table/inverter entries."""
    
    # Pattern to match and strip block prefixes: B01-, B04-, BO4-, etc.
    BLOCK_PREFIX_PATTERN = re.compile(r'^B[O0]?\d+-(.+)$', re.IGNORECASE)
    
    # Patterns to validate extracted names
    TABLE_PATTERN = re.compile(r'^R\d+-[ST]\d+$', re.IGNORECASE)
    INVERTER_PATTERN = re.compile(r'^I\d+$', re.IGNORECASE)
    
    @classmethod
    def extract_clean_name(cls, raw_name: str) -> Optional[str]:
        """
        Extract clean name by stripping block prefix.
        
        Args:
            raw_name: Raw name from Excel like "B01-R42-S01" or "B04-I41"
            
        Returns:
            Clean name like "R42-S01" or "I41", or None if pattern doesn't match
            
        Examples:
            >>> NameExtractor.extract_clean_name("B01-R42-S01")
            'R42-S01'
            >>> NameExtractor.extract_clean_name("B04-I41")
            'I41'
            >>> NameExtractor.extract_clean_name("BO4-R31-S01")
            'R31-S01'
        """
        if not raw_name:
            return None
        
        raw_name = str(raw_name).strip()
        if not raw_name:
            return None
            
        match = cls.BLOCK_PREFIX_PATTERN.match(raw_name)
        if match:
            return match.group(1)
        
        # If no block prefix found, return as-is (might already be clean)
        return raw_name
    
    @classmethod
    def identify_name_type(cls, name: str) -> Optional[str]:
        """
        Identify whether a name is a TABLE or INVERTER.
        
        Args:
            name: Clean name like "R42-S01" or "I41"
            
        Returns:
            "TABLE" or "INVERTER", or None if type cannot be determined
            
        Examples:
            >>> NameExtractor.identify_name_type("R42-S01")
            'TABLE'
            >>> NameExtractor.identify_name_type("R31-T01")
            'TABLE'
            >>> NameExtractor.identify_name_type("I41")
            'INVERTER'
        """
        if not name:
            return None
            
        if cls.TABLE_PATTERN.match(name):
            return "TABLE"
        elif cls.INVERTER_PATTERN.match(name):
            return "INVERTER"
        
        return None
    
    @classmethod
    def validate_table_name(cls, name: str) -> bool:
        """
        Validate that a name follows the TABLE pattern.
        
        Args:
            name: Name to validate (e.g., "R42-S01")
            
        Returns:
            True if valid table name, False otherwise
        """
        return bool(cls.TABLE_PATTERN.match(name))
    
    @classmethod
    def validate_inverter_name(cls, name: str) -> bool:
        """
        Validate that a name follows the INVERTER pattern.
        
        Args:
            name: Name to validate (e.g., "I41")
            
        Returns:
            True if valid inverter name, False otherwise
        """
        return bool(cls.INVERTER_PATTERN.match(name))


class FilePathParser:
    """Handles parsing of complete file paths to extract plot and block information."""
    
    @classmethod
    def parse_excel_path(cls, file_path: str) -> Dict[str, Optional[str]]:
        """
        Parse complete Excel file path to extract plot and block information.
        
        Args:
            file_path: Full path to Excel file
            
        Returns:
            Dictionary with keys: 'plot_name', 'block_name', 'folder_name', 'filename'
            
        Examples:
            >>> path = r"c:\data\A16a - 50 MW\603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx"
            >>> result = FilePathParser.parse_excel_path(path)
            >>> result['plot_name']
            'A-16a'
            >>> result['block_name']
            'BL01'
        """
        path = Path(file_path)
        
        folder_name = path.parent.name
        filename = path.name
        
        plot_name = PlotTransformer.folder_to_plot_name(folder_name)
        block_name = BlockTransformer.filename_to_block_name(filename)
        
        return {
            'plot_name': plot_name,
            'block_name': block_name,
            'folder_name': folder_name,
            'filename': filename
        }
    
    @classmethod
    def extract_plot_and_block(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract plot and block names from file path.
        
        Args:
            file_path: Full path to Excel file
            
        Returns:
            Tuple of (plot_name, block_name)
            
        Examples:
            >>> path = r"c:\data\A16a - 50 MW\*-BL01-*.xlsx"
            >>> FilePathParser.extract_plot_and_block(path)
            ('A-16a', 'BL01')
        """
        parsed = cls.parse_excel_path(file_path)
        return (parsed['plot_name'], parsed['block_name'])


# Test functions for validation
def run_tests():
    """Run tests for all transformer classes."""
    print("="*80)
    print("TRANSFORMATION LOGIC TESTS")
    print("="*80)
    
    # Test PlotTransformer
    print("\n1. Plot Folder → Plot Name Transformation:")
    test_folders = [
        "A16a - 50 MW",
        "A16b - 200 MW",
        "A16c - 167 MW",
        "A16d - 333 MW",
        "S08b - 100 MW"
    ]
    for folder in test_folders:
        plot = PlotTransformer.folder_to_plot_name(folder)
        valid = PlotTransformer.validate_plot_name(plot) if plot else False
        print(f"   {folder:20s} → {plot:10s} [{'✓' if valid else '✗'}]")
    
    # Test BlockTransformer
    print("\n2. Filename → Block Name Extraction:")
    test_files = [
        "603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx",
        "603C-LT Cable Routing A16a-BL04-R0-30032025_DWGData.xlsx",
        "603C-LT Cable Routing-A16a-BL02-R0-30032025_DWGData.xlsx",
        "603C-LT Cable Routing-A16a-BL03-R0-30032025_DWGData.xlsx"
    ]
    for filename in test_files:
        block = BlockTransformer.filename_to_block_name(filename)
        valid = BlockTransformer.validate_block_name(block) if block else False
        print(f"   ...{filename[-40:]:40s} → {block:6s} [{'✓' if valid else '✗'}]")
    
    # Test NameExtractor
    print("\n3. Raw Name → Clean Name Extraction:")
    test_names = [
        ("B01-R42-S01", "TABLE"),
        ("B04-I41", "INVERTER"),
        ("B02-R40-T01", "TABLE"),
        ("B03-I47", "INVERTER"),
        ("BO4-R31-S01", "TABLE"),  # Test with O instead of 0
    ]
    for raw_name, expected_type in test_names:
        clean = NameExtractor.extract_clean_name(raw_name)
        detected_type = NameExtractor.identify_name_type(clean) if clean else None
        match = "✓" if detected_type == expected_type else "✗"
        print(f"   {raw_name:15s} → {clean:10s} [{detected_type:8s}] {match}")
    
    # Test FilePathParser
    print("\n4. Complete Path → Plot + Block Parsing:")
    test_path = r"c:\data\A16a - 50 MW\603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx"
    parsed = FilePathParser.parse_excel_path(test_path)
    print(f"   Path: ...{test_path[-60:]}")
    print(f"   Plot Name:  {parsed['plot_name']}")
    print(f"   Block Name: {parsed['block_name']}")
    print(f"   Folder:     {parsed['folder_name']}")
    
    print("\n" + "="*80)
    print("✅ All transformation tests completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_tests()
