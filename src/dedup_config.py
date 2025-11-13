"""
Deduplication configuration: defines how to handle duplicate entities.

For master data (CLUSTERS, SPVS, VENDORS, etc.), we only need one instance
even if it appears 255 times in Excel. For transactional data (SERVICEORDERS),
each row is unique.
"""

# Entities that should be deduplicated (keep first occurrence only)
DEDUP_ENTITIES = {
    'CLUSTERS': ['NAME'],  # Deduplicate by NAME
    'SPVS': ['NAME'],
    'PROJECTS': ['NAME', 'TYPE', 'CATEGORY'],  # Composite natural key
    'LOCATIONS': ['NAME'],  # Deduplicate by NAME (Excel repeats same location)
    'PLOTS': ['NAME'],  # Deduplicate by NAME (Excel repeats plot for each SO)
    'VENDORS': ['CODE'],
    'PROJECTDEFINITIONS': ['CODE'],
    'PACKAGES': ['NAME'],
}

# Entities that are transactional (never deduplicate)
TRANSACTIONAL_ENTITIES = {
    'SERVICEORDERS',
}


def should_deduplicate(entity: str) -> bool:
    """Check if entity should be deduplicated."""
    return entity in DEDUP_ENTITIES


def get_dedup_keys(entity: str) -> list:
    """Get fields used for deduplication."""
    return DEDUP_ENTITIES.get(entity, [])
