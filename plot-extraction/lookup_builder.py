"""
Lookup Dictionary Builder Module
=================================

This module builds efficient lookup dictionaries from CSV files:
1. Plot Name → PROJECT_ID mapping (from PLOTS-PROJECTS and PLOTS)
2. Existing design elements tracking (from DESIGNELEMENTS)

Date: November 14, 2025
"""

import csv
from pathlib import Path
from typing import Dict, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PlotInfo:
    """Information about a plot."""
    plot_id: str
    plot_name: str
    project_id: str
    location_id: Optional[str] = None


@dataclass
class DesignElement:
    """Existing design element information."""
    id: str
    project_id: str
    name: str
    type: str
    parent_id: str


class LookupDictionaries:
    """Container for all lookup dictionaries."""
    
    def __init__(self):
        # Plot name → PlotInfo
        self.plot_name_to_info: Dict[str, PlotInfo] = {}
        
        # Plot ID → PROJECT_ID
        self.plot_id_to_project_id: Dict[str, str] = {}
        
        # (PROJECT_ID, NAME, TYPE) → DesignElement (for duplicate detection)
        self.existing_elements: Dict[Tuple[str, str, str], DesignElement] = {}
        
        # PROJECT_ID → Set of element IDs
        self.project_elements: Dict[str, Set[str]] = {}
        
        # Element ID → DesignElement (for hierarchy lookup)
        self.elements_by_id: Dict[str, DesignElement] = {}
    
    def get_project_id_for_plot(self, plot_name: str) -> Optional[str]:
        """
        Get PROJECT_ID for a given plot name.
        
        Args:
            plot_name: Plot name like "A-16a"
            
        Returns:
            PROJECT_ID or None if not found
        """
        plot_info = self.plot_name_to_info.get(plot_name.upper())
        return plot_info.project_id if plot_info else None
    
    def get_plot_info(self, plot_name: str) -> Optional[PlotInfo]:
        """
        Get complete plot information.
        
        Args:
            plot_name: Plot name like "A-16a"
            
        Returns:
            PlotInfo object or None if not found
        """
        return self.plot_name_to_info.get(plot_name.upper())
    
    def element_exists(self, project_id: str, name: str, element_type: str) -> bool:
        """
        Check if a design element already exists.
        
        Args:
            project_id: PROJECT_ID
            name: Element name (e.g., "BL01", "R42-S01", "I45")
            element_type: Element type ("PLOT", "BLOCK", "TABLE", "INVERTER")
            
        Returns:
            True if element exists, False otherwise
        """
        key = (project_id.lower(), name.upper(), element_type.upper())
        return key in self.existing_elements
    
    def get_existing_element(self, project_id: str, name: str, element_type: str) -> Optional[DesignElement]:
        """
        Get existing design element.
        
        Args:
            project_id: PROJECT_ID
            name: Element name
            element_type: Element type
            
        Returns:
            DesignElement or None if not found
        """
        key = (project_id.lower(), name.upper(), element_type.upper())
        return self.existing_elements.get(key)
    
    def get_element_by_id(self, element_id: str) -> Optional[DesignElement]:
        """
        Get design element by ID.
        
        Args:
            element_id: Element UUID
            
        Returns:
            DesignElement or None if not found
        """
        return self.elements_by_id.get(element_id.lower())
    
    def add_element(self, element: DesignElement):
        """
        Add an element to the tracking dictionaries (for incremental updates).
        
        Args:
            element: DesignElement to add
        """
        key = (element.project_id.lower(), element.name.upper(), element.type.upper())
        self.existing_elements[key] = element
        self.elements_by_id[element.id.lower()] = element
        
        if element.project_id not in self.project_elements:
            self.project_elements[element.project_id] = set()
        self.project_elements[element.project_id].add(element.id)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded data."""
        return {
            'plots': len(self.plot_name_to_info),
            'existing_elements': len(self.existing_elements),
            'unique_projects': len(self.project_elements),
            'elements_by_id': len(self.elements_by_id)
        }


def load_plots_projects_mapping(csv_path: str) -> Dict[str, Tuple[str, str]]:
    """
    Load PLOTS-PROJECTS.csv to get PLOT_ID → (PROJECT_ID, PLOT_NAME) mapping.
    
    Args:
        csv_path: Path to CCTECH.DRS.ENTITIES-PLOTS-PROJECTS.csv
        
    Returns:
        Dictionary: {PLOT_ID: (PROJECT_ID, PLOT_NAME)}
        
    CSV Structure:
        ID,PROJECT_ID,PLOT_ID,PLOT_NAME
    """
    mapping = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plot_id = row['PLOT_ID'].strip()
            project_id = row['PROJECT_ID'].strip()
            plot_name = row['PLOT_NAME'].strip()
            mapping[plot_id] = (project_id, plot_name)
    
    return mapping


def load_plots_info(csv_path: str) -> Dict[str, Dict[str, str]]:
    """
    Load PLOTS.csv to get PLOT_ID → plot details mapping.
    
    Args:
        csv_path: Path to CCTECH.DRS.ENTITIES-PLOTS.csv
        
    Returns:
        Dictionary: {PLOT_ID: {ID, LOCATION_ID, NAME, DESIGN_ELEMENT_ID}}
        
    CSV Structure:
        ID,LOCATION_ID,NAME,DESIGN_ELEMENT_ID
    """
    plots = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plot_id = row['ID'].strip()
            plots[plot_id] = {
                'id': plot_id,
                'location_id': row['LOCATION_ID'].strip(),
                'name': row['NAME'].strip(),
                'design_element_id': row.get('DESIGN_ELEMENT_ID', '').strip()
            }
    
    return plots


def load_existing_design_elements(csv_path: str) -> Dict[Tuple[str, str, str], DesignElement]:
    """
    Load DESIGNELEMENTS.csv to track existing elements.
    
    Args:
        csv_path: Path to CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv
        
    Returns:
        Dictionary: {(PROJECT_ID, NAME, TYPE): DesignElement}
        
    CSV Structure:
        ID,PROJECT_ID,NAME,TYPE,PARENT_ID
    """
    elements = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            element = DesignElement(
                id=row['ID'].strip(),
                project_id=row['PROJECT_ID'].strip(),
                name=row['NAME'].strip(),
                type=row['TYPE'].strip(),
                parent_id=row.get('PARENT_ID', '').strip()
            )
            
            # Create lookup key (case-insensitive for matching)
            key = (
                element.project_id.lower(),
                element.name.upper(),
                element.type.upper()
            )
            elements[key] = element
    
    return elements


def build_lookup_dictionaries(
    plots_projects_csv: str,
    plots_csv: str,
    design_elements_csv: str
) -> LookupDictionaries:
    """
    Build all lookup dictionaries from CSV files.
    
    Args:
        plots_projects_csv: Path to PLOTS-PROJECTS.csv
        plots_csv: Path to PLOTS.csv
        design_elements_csv: Path to DESIGNELEMENTS.csv
        
    Returns:
        LookupDictionaries object with all mappings loaded
    """
    lookups = LookupDictionaries()
    
    print("🔄 Loading lookup dictionaries...")
    
    # Load PLOTS-PROJECTS mapping
    print(f"   📄 Loading {Path(plots_projects_csv).name}...")
    plots_projects = load_plots_projects_mapping(plots_projects_csv)
    print(f"      ✅ Loaded {len(plots_projects)} plot-project mappings")
    
    # Load PLOTS info
    print(f"   📄 Loading {Path(plots_csv).name}...")
    plots_info = load_plots_info(plots_csv)
    print(f"      ✅ Loaded {len(plots_info)} plots")
    
    # Build plot name → info mapping
    for plot_id, (project_id, plot_name) in plots_projects.items():
        plot_details = plots_info.get(plot_id, {})
        
        plot_info = PlotInfo(
            plot_id=plot_id,
            plot_name=plot_name,
            project_id=project_id,
            location_id=plot_details.get('location_id')
        )
        
        # Store with uppercase plot name for case-insensitive lookup
        lookups.plot_name_to_info[plot_name.upper()] = plot_info
        lookups.plot_id_to_project_id[plot_id] = project_id
    
    # Load existing design elements
    print(f"   📄 Loading {Path(design_elements_csv).name}...")
    existing_elements = load_existing_design_elements(design_elements_csv)
    lookups.existing_elements = existing_elements
    print(f"      ✅ Loaded {len(existing_elements)} existing design elements")
    
    # Build additional indexes
    for element in existing_elements.values():
        lookups.elements_by_id[element.id.lower()] = element
        
        if element.project_id not in lookups.project_elements:
            lookups.project_elements[element.project_id] = set()
        lookups.project_elements[element.project_id].add(element.id)
    
    print("   ✅ All lookup dictionaries loaded successfully!")
    
    return lookups


def test_lookups():
    """Test the lookup dictionaries with sample data."""
    print("="*80)
    print("LOOKUP DICTIONARIES TEST")
    print("="*80)
    
    # Define paths
    base_path = Path(r"c:\Users\Shamshad choudhary\Documents\Pulse-Data-Uploading-Scripts\plot-extraction\data")
    plots_projects_csv = base_path / "CCTECH.DRS.ENTITIES-PLOTS-PROJECTS.csv"
    plots_csv = base_path / "CCTECH.DRS.ENTITIES-PLOTS.csv"
    design_elements_csv = base_path / "CCTECH.DRS.ENTITIES-DESIGNELEMENTS.csv"
    
    # Build lookups
    lookups = build_lookup_dictionaries(
        str(plots_projects_csv),
        str(plots_csv),
        str(design_elements_csv)
    )
    
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    stats = lookups.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value:,}")
    
    # Test plot lookups
    print("\n" + "="*80)
    print("TEST: Plot Name → PROJECT_ID Lookup")
    print("="*80)
    
    test_plots = ["A-16a", "A-16b", "A-16c", "A-16d", "S-05b", "NONEXISTENT"]
    
    for plot_name in test_plots:
        project_id = lookups.get_project_id_for_plot(plot_name)
        plot_info = lookups.get_plot_info(plot_name)
        
        if project_id:
            print(f"   ✅ '{plot_name}' → PROJECT_ID: {project_id}")
            if plot_info:
                print(f"      PLOT_ID: {plot_info.plot_id}")
        else:
            print(f"   ❌ '{plot_name}' → Not found")
    
    # Test duplicate detection
    print("\n" + "="*80)
    print("TEST: Duplicate Detection")
    print("="*80)
    
    # Get a valid PROJECT_ID for testing
    test_project_id = lookups.get_project_id_for_plot("A-16a") or "661fc43c-e164-41e0-939f-16c15d014fa9"
    
    test_elements = [
        (test_project_id, "BL01", "BLOCK"),
        (test_project_id, "R42-S01", "TABLE"),
        (test_project_id, "I45", "INVERTER"),
        (test_project_id, "NEW-ELEMENT", "TABLE"),
    ]
    
    for project_id, name, element_type in test_elements:
        exists = lookups.element_exists(project_id, name, element_type)
        status = "⚠️  EXISTS" if exists else "✅ NEW"
        print(f"   {status}: ({project_id[:8]}..., {name}, {element_type})")
        
        if exists:
            element = lookups.get_existing_element(project_id, name, element_type)
            if element:
                print(f"      ID: {element.id}")
                print(f"      PARENT_ID: {element.parent_id}")
    
    # Test element by ID lookup
    print("\n" + "="*80)
    print("TEST: Element by ID Lookup")
    print("="*80)
    
    # Get a sample element ID
    if lookups.existing_elements:
        sample_element = next(iter(lookups.existing_elements.values()))
        element = lookups.get_element_by_id(sample_element.id)
        
        if element:
            print(f"   ✅ Found element by ID: {element.id}")
            print(f"      Name: {element.name}")
            print(f"      Type: {element.type}")
            print(f"      PROJECT_ID: {element.project_id}")
            print(f"      PARENT_ID: {element.parent_id}")
    
    print("\n" + "="*80)
    print("✅ All tests completed!")
    print("="*80)


if __name__ == "__main__":
    test_lookups()
