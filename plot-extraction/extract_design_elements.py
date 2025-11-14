"""
Design Elements Extraction Script
==================================

This script extracts design elements from Excel files in drawing_data/ folders
and creates a hierarchical structure:
    PLOT (from folder) → BLOCK (from filename) → TABLE/INVERTER (from Excel rows)

Date: November 14, 2025
"""

import csv
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import openpyxl

from transform_logic import (
    folder_to_plot_name,
    filename_to_block_name,
    filename_to_plot_name,
    extract_table_and_inverter,
    validate_plot_consistency
)
from lookup_builder import build_lookup_dictionaries, LookupDictionaries


@dataclass
class NewDesignElement:
    """A new design element to be added."""
    id: str
    project_id: str
    name: str
    type: str
    parent_id: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for CSV writing."""
        return {
            'ID': self.id,
            'PROJECT_ID': self.project_id,
            'NAME': self.name,
            'TYPE': self.type,
            'PARENT_ID': self.parent_id
        }


@dataclass
class ExtractionStats:
    """Statistics for the extraction process."""
    plots_processed: int = 0
    blocks_processed: int = 0
    tables_extracted: int = 0
    inverters_extracted: int = 0
    plots_created: int = 0
    blocks_created: int = 0
    tables_created: int = 0
    inverters_created: int = 0
    plots_skipped: int = 0
    blocks_skipped: int = 0
    tables_skipped: int = 0
    inverters_skipped: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def total_extracted(self) -> int:
        """Total elements extracted from Excel."""
        return self.tables_extracted + self.inverters_extracted
    
    def total_created(self) -> int:
        """Total new elements created."""
        return self.plots_created + self.blocks_created + self.tables_created + self.inverters_created
    
    def total_skipped(self) -> int:
        """Total elements skipped (duplicates)."""
        return self.plots_skipped + self.blocks_skipped + self.tables_skipped + self.inverters_skipped


class DesignElementExtractor:
    """Extracts design elements from Excel files."""
    
    def __init__(self, lookups: LookupDictionaries):
        self.lookups = lookups
        self.stats = ExtractionStats()
        self.new_elements: List[NewDesignElement] = []
        
        # Track created elements in this session (to avoid duplicates within extraction)
        self.session_elements: Dict[Tuple[str, str, str], NewDesignElement] = {}
    
    def _create_element(
        self,
        project_id: str,
        name: str,
        element_type: str,
        parent_id: str = ""
    ) -> Optional[NewDesignElement]:
        """
        Create a new design element if it doesn't exist.
        
        Args:
            project_id: PROJECT_ID
            name: Element name
            element_type: PLOT, BLOCK, TABLE, INVERTER
            parent_id: Parent element UUID (empty for PLOT)
            
        Returns:
            NewDesignElement if created, None if duplicate
        """
        # Check if element already exists in CSV
        if self.lookups.element_exists(project_id, name, element_type):
            return None
        
        # Check if element was created in this session
        key = (project_id.lower(), name.upper(), element_type.upper())
        if key in self.session_elements:
            return self.session_elements[key]
        
        # Create new element
        element = NewDesignElement(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            type=element_type,
            parent_id=parent_id
        )
        
        # Track in session
        self.session_elements[key] = element
        self.new_elements.append(element)
        
        return element
    
    def _get_or_create_plot(
        self,
        project_id: str,
        plot_name: str
    ) -> Tuple[Optional[str], bool]:
        """
        Get existing PLOT element ID or create new one.
        
        Args:
            project_id: PROJECT_ID
            plot_name: Plot name (e.g., "A-16a")
            
        Returns:
            (plot_element_id, was_created)
        """
        self.stats.plots_processed += 1
        
        # Check existing
        existing = self.lookups.get_existing_element(project_id, plot_name, "PLOT")
        if existing:
            self.stats.plots_skipped += 1
            return existing.id, False
        
        # Check session
        key = (project_id.lower(), plot_name.upper(), "PLOT")
        if key in self.session_elements:
            return self.session_elements[key].id, False
        
        # Create new PLOT
        plot_element = self._create_element(project_id, plot_name, "PLOT", parent_id="")
        if plot_element:
            self.stats.plots_created += 1
            return plot_element.id, True
        
        return None, False
    
    def _get_or_create_block(
        self,
        project_id: str,
        block_name: str,
        plot_element_id: str
    ) -> Tuple[Optional[str], bool]:
        """
        Get existing BLOCK element ID or create new one.
        
        Args:
            project_id: PROJECT_ID
            block_name: Block name (e.g., "BL01")
            plot_element_id: Parent PLOT element ID
            
        Returns:
            (block_element_id, was_created)
        """
        self.stats.blocks_processed += 1
        
        # Check existing
        existing = self.lookups.get_existing_element(project_id, block_name, "BLOCK")
        if existing:
            self.stats.blocks_skipped += 1
            return existing.id, False
        
        # Check session
        key = (project_id.lower(), block_name.upper(), "BLOCK")
        if key in self.session_elements:
            return self.session_elements[key].id, False
        
        # Create new BLOCK
        block_element = self._create_element(
            project_id, block_name, "BLOCK", parent_id=plot_element_id
        )
        if block_element:
            self.stats.blocks_created += 1
            return block_element.id, True
        
        return None, False
    
    def _create_table_or_inverter(
        self,
        project_id: str,
        name: str,
        element_type: str,
        block_element_id: str
    ) -> bool:
        """
        Create TABLE or INVERTER element.
        
        Args:
            project_id: PROJECT_ID
            name: Element name (e.g., "R42-S01", "I45")
            element_type: "TABLE" or "INVERTER"
            block_element_id: Parent BLOCK element ID
            
        Returns:
            True if created, False if duplicate
        """
        # Track extraction
        if element_type == "TABLE":
            self.stats.tables_extracted += 1
        else:
            self.stats.inverters_extracted += 1
        
        # Check existing
        if self.lookups.element_exists(project_id, name, element_type):
            if element_type == "TABLE":
                self.stats.tables_skipped += 1
            else:
                self.stats.inverters_skipped += 1
            return False
        
        # Check session
        key = (project_id.lower(), name.upper(), element_type.upper())
        if key in self.session_elements:
            if element_type == "TABLE":
                self.stats.tables_skipped += 1
            else:
                self.stats.inverters_skipped += 1
            return False
        
        # Create new element
        element = self._create_element(
            project_id, name, element_type, parent_id=block_element_id
        )
        
        if element:
            if element_type == "TABLE":
                self.stats.tables_created += 1
            else:
                self.stats.inverters_created += 1
            return True
        
        return False
    
    def process_excel_file(
        self,
        excel_path: Path,
        plot_name: str,
        project_id: str
    ) -> bool:
        """
        Process a single Excel file and extract design elements.
        
        Args:
            excel_path: Path to Excel file
            plot_name: Plot name (e.g., "A-16a")
            project_id: PROJECT_ID
            
        Returns:
            True if successful, False if errors occurred
        """
        try:
            # Extract block name from filename
            block_name = filename_to_block_name(excel_path.name)
            if not block_name:
                error_msg = f"❌ Failed to extract block name from: {excel_path.name}"
                self.stats.errors.append(error_msg)
                print(f"   {error_msg}")
                return False
            
            # Validate plot consistency
            filename_plot = filename_to_plot_name(excel_path.name)
            if not validate_plot_consistency(plot_name, filename_plot):
                error_msg = f"⚠️  Plot name mismatch: folder={plot_name}, file={filename_plot} (from {excel_path.name})"
                self.stats.errors.append(error_msg)
                print(f"   {error_msg}")
            
            # Get or create PLOT element
            plot_element_id, plot_created = self._get_or_create_plot(project_id, plot_name)
            if not plot_element_id:
                error_msg = f"❌ Failed to get/create PLOT for: {plot_name}"
                self.stats.errors.append(error_msg)
                print(f"   {error_msg}")
                return False
            
            # Get or create BLOCK element
            block_element_id, block_created = self._get_or_create_block(
                project_id, block_name, plot_element_id
            )
            if not block_element_id:
                error_msg = f"❌ Failed to get/create BLOCK for: {block_name}"
                self.stats.errors.append(error_msg)
                print(f"   {error_msg}")
                return False
            
            # Read Excel file
            wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
            ws = wb.active
            
            # Process rows (skip header row 1)
            rows_processed = 0
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                # Extract table and inverter names
                table_name, inverter_name = extract_table_and_inverter(row)
                
                # Create TABLE element if present
                if table_name:
                    self._create_table_or_inverter(
                        project_id, table_name, "TABLE", block_element_id
                    )
                
                # Create INVERTER element if present
                if inverter_name:
                    self._create_table_or_inverter(
                        project_id, inverter_name, "INVERTER", block_element_id
                    )
                
                rows_processed += 1
            
            wb.close()
            
            status = "✅" if rows_processed > 0 else "⚠️"
            print(f"   {status} {excel_path.name}: {rows_processed} rows processed")
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Error processing {excel_path.name}: {str(e)}"
            self.stats.errors.append(error_msg)
            print(f"   {error_msg}")
            return False
    
    def process_plot_folder(self, plot_folder: Path) -> bool:
        """
        Process all Excel files in a plot folder.
        
        Args:
            plot_folder: Path to plot folder (e.g., "A16a - 50 MW")
            
        Returns:
            True if successful, False if errors occurred
        """
        # Extract plot name from folder
        plot_name = folder_to_plot_name(plot_folder.name)
        if not plot_name:
            error_msg = f"❌ Failed to extract plot name from folder: {plot_folder.name}"
            self.stats.errors.append(error_msg)
            print(f"   {error_msg}")
            return False
        
        # Get PROJECT_ID
        project_id = self.lookups.get_project_id_for_plot(plot_name)
        if not project_id:
            error_msg = f"❌ No PROJECT_ID found for plot: {plot_name}"
            self.stats.errors.append(error_msg)
            print(f"   {error_msg}")
            return False
        
        print(f"\n📁 Processing: {plot_folder.name} → {plot_name}")
        print(f"   PROJECT_ID: {project_id}")
        
        # Find all Excel files
        excel_files = list(plot_folder.glob("*.xlsx"))
        if not excel_files:
            print(f"   ⚠️  No Excel files found")
            return True
        
        print(f"   📊 Found {len(excel_files)} Excel file(s)")
        
        # Process each Excel file
        success = True
        for excel_file in sorted(excel_files):
            if not self.process_excel_file(excel_file, plot_name, project_id):
                success = False
        
        return success
    
    def extract_all(self, drawing_data_path: Path) -> bool:
        """
        Extract design elements from all plot folders.
        
        Args:
            drawing_data_path: Path to drawing_data/ folder
            
        Returns:
            True if successful, False if errors occurred
        """
        print("="*80)
        print("DESIGN ELEMENTS EXTRACTION")
        print("="*80)
        
        # Find all plot folders
        plot_folders = [f for f in drawing_data_path.iterdir() if f.is_dir()]
        if not plot_folders:
            print("❌ No plot folders found in drawing_data/")
            return False
        
        print(f"\n🔍 Found {len(plot_folders)} plot folder(s)")
        
        # Process each plot folder
        success = True
        for plot_folder in sorted(plot_folders):
            if not self.process_plot_folder(plot_folder):
                success = False
        
        return success
    
    def print_summary(self):
        """Print extraction summary."""
        print("\n" + "="*80)
        print("EXTRACTION SUMMARY")
        print("="*80)
        
        print(f"\n📊 Elements Extracted from Excel:")
        print(f"   Tables:    {self.stats.tables_extracted:,}")
        print(f"   Inverters: {self.stats.inverters_extracted:,}")
        print(f"   Total:     {self.stats.total_extracted():,}")
        
        print(f"\n✅ New Elements Created:")
        print(f"   Plots:     {self.stats.plots_created:,}")
        print(f"   Blocks:    {self.stats.blocks_created:,}")
        print(f"   Tables:    {self.stats.tables_created:,}")
        print(f"   Inverters: {self.stats.inverters_created:,}")
        print(f"   Total:     {self.stats.total_created():,}")
        
        print(f"\n⚠️  Elements Skipped (Duplicates):")
        print(f"   Plots:     {self.stats.plots_skipped:,}")
        print(f"   Blocks:    {self.stats.blocks_skipped:,}")
        print(f"   Tables:    {self.stats.tables_skipped:,}")
        print(f"   Inverters: {self.stats.inverters_skipped:,}")
        print(f"   Total:     {self.stats.total_skipped():,}")
        
        print(f"\n📈 Processing Stats:")
        print(f"   Plots processed:  {self.stats.plots_processed}")
        print(f"   Blocks processed: {self.stats.blocks_processed}")
        
        if self.stats.errors:
            print(f"\n❌ Errors: {len(self.stats.errors)}")
            for error in self.stats.errors[:10]:  # Show first 10 errors
                print(f"   {error}")
            if len(self.stats.errors) > 10:
                print(f"   ... and {len(self.stats.errors) - 10} more errors")
        else:
            print(f"\n✅ No errors encountered")


def main():
    """Main extraction function."""
    
    # Define paths
    base_path = Path(r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction")
    data_path = base_path / "data"
    drawing_data_path = base_path / "drawing_data"
    
    # Build lookup dictionaries
    print("🔄 Loading lookup dictionaries...")
    lookups = build_lookup_dictionaries(
        str(data_path / "CCTECH.DRS.ENTITIES-PLOTS-PROJECTS.csv"),
        str(data_path / "CCTECH.DRS.ENTITIES-PLOTS.csv"),
        str(data_path / "CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv")
    )
    print("   ✅ Lookups loaded!\n")
    
    # Create extractor
    extractor = DesignElementExtractor(lookups)
    
    # Extract all elements
    success = extractor.extract_all(drawing_data_path)
    
    # Print summary
    extractor.print_summary()
    
    # Save results
    if extractor.new_elements:
        output_file = base_path / "output" / "new_design_elements.csv"
        output_file.parent.mkdir(exist_ok=True)
        
        print(f"\n💾 Saving {len(extractor.new_elements)} new elements to: {output_file.name}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['ID', 'PROJECT_ID', 'NAME', 'TYPE', 'PARENT_ID']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for element in extractor.new_elements:
                writer.writerow(element.to_dict())
        
        print(f"   ✅ Saved to: {output_file}")
    else:
        print("\n⚠️  No new elements to save (all elements already exist)")
    
    print("\n" + "="*80)
    if success and not extractor.stats.errors:
        print("✅ EXTRACTION COMPLETED SUCCESSFULLY!")
    elif success and extractor.stats.errors:
        print("⚠️  EXTRACTION COMPLETED WITH WARNINGS")
    else:
        print("❌ EXTRACTION COMPLETED WITH ERRORS")
    print("="*80)


if __name__ == "__main__":
    main()
